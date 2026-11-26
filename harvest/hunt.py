import gzip, json, os, re, sys, time, urllib.parse, urllib.request
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import yt_events as E
os.environ['MODE'] = 'lib'
import yt_shows as YS
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
IN = os.path.join(ROOT, 'catalog', os.environ.get('ITEMS', 'hunt_items.json')); OUT = os.path.join(ROOT, 'catalog', os.environ.get('OUTF', 'hunt_found.json'))
SH = int(os.environ.get('SHARD', '0')); NS = int(os.environ.get('NSHARD', '1'))
HEVC = re.compile(r'(?i)x265|hevc|h\.?265|10bit|10-bit')
UA = {'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36'}
JUNK = re.compile(r"(?i)lektor|dublado|dublada|doblaje|latino|espa[nñ]ol|castellano|deutsch|german|fran[cç]ais|\bvf\b|italiano|russian|polski|hindi|montaj|watch party|first time watching|reacts|my thoughts|dark side of|music only|episode \d+ - |reaction|review|trailer|teaser|clip\b|scene\b|behind the scenes|making of|interview|podcast|commentary|explained|facts|secrets|everything wrong|nostalgia critic|ranking|ranked|top \d+|parody|\bytp\b|karaoke|lyrics|soundtrack|\bost\b|audio ?book|read ?aloud|play at|theatre|theater company|high school|musical\b|recap|analysis|lookback|look back|retrospective|tribute|compilation|shorts\b|#shorts|tiktok|\b(2005|20[1-2]\d)\b(?!\s*(upload|transfer|remaster))")
def get(url, tries=4):
    for i in range(tries):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=40) as r: return json.loads(r.read().decode('utf-8', 'replace'))
        except Exception as e:
            if i == tries - 1: print('fail', url[:120], e, flush=True)
            time.sleep(3 + 4 * i)
    return None
def secs(s):
    try:
        s = str(s)
        if ':' in s:
            p = [float(x) for x in s.split(':')]; v = 0
            for x in p: v = v * 60 + x
            return v
        return float(s)
    except Exception: return 0
def ia_files(ident):
    j = get('https://archive.org/metadata/' + urllib.parse.quote(ident))
    if not j or not j.get('files') or j.get('is_dark'): return None, {}
    m = j.get('metadata', {})
    if str(m.get('access-restricted-item', '')).lower() == 'true': return None, m
    out = []; seen = set()
    for f in j['files']:
        n = f.get('name', '')
        if not n.lower().endswith(('.mp4', '.m4v')): continue
        key = f.get('original') if f.get('source') == 'derivative' else n
        d = secs(f.get('length') or 0)
        if key in seen and not d: continue
        seen.add(key)
        if d >= 60: out.append([n, round(d)])
    return out, m
items = json.load(open(IN, encoding='utf-8'))
only = set(x for x in os.environ.get('ONLY', '').split('|') if x)
res = json.load(open(OUT, encoding='utf-8')) if os.path.exists(OUT) else {}
for ii, it in enumerate(items):
    k = it['k']
    if only and k not in only: continue
    if ii % NS != SH: continue
    must = re.compile('(?i)' + it['must']); lo, hi = it.get('lo', 600), it.get('hi', 12000)
    RAW = bool(it.get('raw'))
    sm = re.compile('(?i)' + it['sm']) if it.get('sm') else None; fm = re.compile('(?i)' + it['fm']) if it.get('fm') else None
    ia = {}; yt = {}
    for q in it.get('ia', []):
        j = get('https://archive.org/advancedsearch.php?' + urllib.parse.urlencode({'q': q, 'fl[]': ['identifier', 'title', 'downloads', 'year', 'language'], 'rows': 200 if RAW else 60, 'sort[]': 'downloads desc', 'output': 'json'}, doseq=True))
        for d in (j or {}).get('response', {}).get('docs', []):
            t = str(d.get('title') or ''); i = d['identifier']
            ii2 = i.replace('-', ' ').replace('_', ' ')
            hit = must.search(t) or must.search(ii2)
            if i in ia or not (hit or (sm and (sm.search(t) or sm.search(ii2)))) or (JUNK.search(t) and not RAW): continue
            ia[i] = {'id': i, 't': t[:160], 'y': str(d.get('year') or ''), 'dl': int(d.get('downloads') or 0), 'lang': str(d.get('language') or '')[:30], 'hit': bool(hit)}
    for i, d in sorted(ia.items(), key=lambda x: -x[1]['dl'])[:80 if RAW else 25]:
        f, m = ia_files(i)
        d['files'] = [x for x in (f or []) if lo * 0.5 <= x[1] <= hi * 1.2 and not HEVC.search(x[0])] if f else []
        if fm and not d.get('hit'): d['files'] = [x for x in d['files'] if fm.search(x[0].replace('_', ' ').replace('.', ' '))]
        if fm and not d.get('hit') and not d['files']: ia.pop(i); continue
        d['tot'] = sum(x[1] for x in (f or []))
        d['desc'] = re.sub(r'<[^>]+>', ' ', str(m.get('description') or ''))[:200] if m else ''
        if not d['files'] and not (lo <= d['tot'] <= hi): ia.pop(i)
    for i in [i for i, d in ia.items() if 'files' not in d]: ia.pop(i)
    for q in it.get('yt', []):
        try: rs = E.search(q, pages=2, long=False)
        except Exception as e: print('ytfail', q, e, flush=True); continue
        for r in rs:
            t = r.get('t') or ''; d = int(r.get('dur') or 0)
            if r['vid'] in yt or not must.search(t) or ((JUNK.search(t) or not (lo <= d <= hi)) and not RAW): continue
            yt[r['vid']] = {'vid': r['vid'], 't': t[:160], 'ch': (r.get('ch') or '')[:60], 'dur': d, 'q': q}
    ytl = list(yt.values())[:200 if RAW else 20]
    res[k] = {'ia': sorted(ia.values(), key=lambda x: -x['dl'])[:80 if RAW else 15], 'yt': ytl, 'at': time.strftime('%Y-%m-%d')}
    print(k, 'ia', len(res[k]['ia']), 'yt', len(res[k]['yt']), flush=True)
ck = res.setdefault('_check', {})
for v in [x for x in os.environ.get('CHECK', '').split('|') if x]:
    try: r = YS.player(v) or {}
    except Exception as e: r = {'perr': str(e)[:80]}
    try:
        j = get('https://www.youtube.com/oembed?format=json&url=' + urllib.parse.quote('https://www.youtube.com/watch?v=' + v, safe=''), tries=2)
        if j: r['t'] = j.get('title', ''); r['ch'] = j.get('author_name', '')
    except Exception: pass
    ck[v] = r; print('check', v, r.get('status'), r.get('dur'), r.get('t', '')[:60], flush=True)
json.dump(res, open(OUT, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
