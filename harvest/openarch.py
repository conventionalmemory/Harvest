import gzip, json, os, re, struct, sys, time, collections, urllib.parse, urllib.request
from concurrent.futures import ThreadPoolExecutor
MODE = os.environ.get('MODE', 'run')
OUT = 'catalog/openarch.json.gz'
UA = 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0 Safari/537.36'
T0 = time.time()
BUDGET = float(os.environ.get('BUDGET_MIN', '150')) * 60
def left(): return BUDGET - (time.time() - T0)
def req(url, rng=None, method='GET', timeout=40, tries=3, headers=None, data=None):
    last = None
    for k in range(tries):
        try:
            h = {'User-Agent': UA, 'Accept': '*/*'}
            if rng: h['Range'] = 'bytes=%d-%d' % rng
            if headers: h.update(headers)
            r = urllib.request.Request(url, headers=h, method=method, data=data)
            with urllib.request.urlopen(r, timeout=timeout) as f:
                body = f.read()
                return f.status, dict((a.lower(), b) for a, b in f.headers.items()), body, f.geturl()
        except urllib.error.HTTPError as e:
            last = (e.code, dict((a.lower(), b) for a, b in e.headers.items()), b'', url)
            if e.code in (429, 500, 502, 503, 504): time.sleep(4 + 6 * k); continue
            return last
        except Exception as e:
            last = (0, {'error': str(e)[:120]}, b'', url); time.sleep(2 + 3 * k)
    return last
def jget(url, **kw):
    st, hd, body, _ = req(url, **kw)
    if st != 200: return None
    try: return json.loads(body.decode('utf-8', 'replace'))
    except Exception: return None
def mp4dur(url):
    st, hd, body, fin = req(url, rng=(0, 65535), timeout=30)
    if st not in (200, 206): return None, st, hd
    ct = hd.get('content-type', '')
    total = 0
    m = re.search(r'/(\d+)$', hd.get('content-range', ''))
    if m: total = int(m.group(1))
    def mv(buf):
        i = buf.find(b'mvhd')
        if i < 0 or i + 32 > len(buf): return None
        ver = buf[i + 4]
        if ver == 1:
            if i + 40 > len(buf): return None
            ts, du = struct.unpack('>IQ', buf[i + 24:i + 36])
        else:
            ts, du = struct.unpack('>II', buf[i + 16:i + 24])
        return du / ts if ts else None
    d = mv(body)
    if d: return d, st, hd
    off = 0; buf = body
    for hop in range(14):
        if off + 16 > len(buf):
            s2, h2, b2, _ = req(url, rng=(off, off + 15), timeout=30)
            if s2 != 206 or len(b2) < 8: return None, st, hd
            head = b2
        else:
            head = buf[off:off + 16]
        size, typ = struct.unpack('>I4s', head[:8])
        if size == 1 and len(head) >= 16: size = struct.unpack('>Q', head[8:16])[0]
        if typ == b'moov':
            s2, h2, b2, _ = req(url, rng=(off, off + 4095), timeout=30)
            if s2 != 206: return None, st, hd
            return mv(b2), st, hd
        if size < 8: break
        off += size
        if total and off >= total: break
        buf = b''
    if total > 400000:
        s2, h2, b2, _ = req(url, rng=(total - 400000, total - 1), timeout=40)
        if s2 == 206:
            d = mv(b2)
            if d: return d, st, hd
    return None, st, hd
def show(tag, url, extra=''):
    d, st, hd = mp4dur(url)
    print('  SAMPLE', tag, '|', url[:150], '| status', st, '| type', hd.get('content-type'), '| ranges', hd.get('accept-ranges'), '| cors', hd.get('access-control-allow-origin'), '| len', hd.get('content-range') or hd.get('content-length'), '| dur', d and round(d), '|', extra[:90], flush=True)
    return d, st, hd
def probe():
    print('== NASA')
    for q, extra in (('STS-31', ''), ('space shuttle launch', '&year_start=1984&year_end=2004'), ('shuttle', '&year_start=1990&year_end=1990'), ('Challenger', ''), ('mission highlights', ''), ('STS-61 Hubble', ''), ('launch', '&year_start=1995&year_end=1995'), ('Mars Pathfinder', ''), ('resource tape', ''), ('post flight presentation', '')):
        j = jget('https://images-api.nasa.gov/search?q=%s&media_type=video&page_size=100%s' % (urllib.parse.quote(q), extra))
        its = (j or {}).get('collection', {}).get('items') or []
        print(' q', q, extra, 'hits', (j or {}).get('collection', {}).get('metadata'), 'years', sorted(collections.Counter(str(i['data'][0].get('date_created'))[:4] for i in its).items()))
        for it in its[:3]:
            d0 = it['data'][0]
            a = jget('https://images-api.nasa.gov/asset/' + urllib.parse.quote(d0['nasa_id']))
            hs = [x['href'] for x in (a or {}).get('collection', {}).get('items', [])]
            print('  ', d0['nasa_id'], d0.get('date_created'), '|', str(d0.get('title'))[:70], '|', str(d0.get('description'))[:160].replace('\n', ' '), '|', d0.get('center'), [h.rsplit('~', 1)[-1] for h in hs])
            v = [h for h in hs if h.lower().endswith('.mp4')]
            if v: show('nasa', urllib.parse.quote(v[0].replace('http://', 'https://'), safe=':/~'), str(d0.get('title')))
    print('== COMMONS')
    for cat in ('Videos of State of the Union addresses', 'Videos of Space Shuttle launches', 'Videos of Ronald Reagan', 'Videos of Bill Clinton', 'Videos of George H. W. Bush', 'Videos by C-SPAN', 'Videos from the White House', 'Videos of the Space Shuttle Challenger disaster', 'Videos of Space Shuttle missions', 'Videos from NASA', 'Videos of United States presidential debates', 'Videos of presidential inaugurations of the United States'):
        j = jget('https://commons.wikimedia.org/w/api.php?action=query&format=json&generator=categorymembers&gcmtitle=' + urllib.parse.quote('Category:' + cat) + '&gcmtype=file|subcat&gcmlimit=60&prop=videoinfo&viprop=url|size|mime|derivatives|extmetadata&viextmetadatafilter=DateTimeOriginal|LicenseShortName|ObjectName')
        pg = list(((j or {}).get('query') or {}).get('pages', {}).values())
        fs = [p for p in pg if p.get('videoinfo')]
        print(' cat', cat, 'members', len(pg), 'videos', len(fs), 'subcats', [p['title'] for p in pg if p.get('ns') == 14][:12])
        for p in fs[:4]:
            vi = p['videoinfo'][0]; em = vi.get('extmetadata') or {}
            print('   ', p['title'][:80], '| dur', vi.get('duration'), '| mime', vi.get('mime'), '| date', (em.get('DateTimeOriginal') or {}).get('value', '')[:60], '| lic', (em.get('LicenseShortName') or {}).get('value'), '| deriv', [(d.get('transcodekey') or d.get('shorttitle'), d.get('type')) for d in (vi.get('derivatives') or [])][:8])
            ds = [d for d in (vi.get('derivatives') or []) if '480p' in str(d.get('transcodekey') or d.get('src'))] or (vi.get('derivatives') or [])
            if ds:
                st, hd, body, fin = req(ds[0]['src'], rng=(0, 2047))
                print('     SAMPLE commons', ds[0]['src'][:140], st, hd.get('content-type'), hd.get('accept-ranges'), hd.get('access-control-allow-origin'), hd.get('content-range'))
        time.sleep(1)
    print('== MILLER')
    for u in ('https://millercenter.org/the-presidency/presidential-speeches', 'https://millercenter.org/the-presidency/presidential-speeches/january-28-1986-address-space-shuttle-challenger-disaster', 'https://millercenter.org/the-presidency/presidential-speeches/january-20-1993-first-inaugural', 'https://millercenter.org/the-presidency/presidential-speeches/september-11-2001-address-nation-terrorist-attacks', 'https://millercenter.org/the-presidency/presidential-speeches/june-12-1987-address-berlin-wall-brandenburg-gate', 'https://millercenter.org/the-presidency/presidential-speeches/january-16-1991-address-nation-invasion-iraq'):
        st, hd, body, fin = req(u)
        print(' ', u[-70:], st, len(body), [x.decode() for x in set(re.findall(rb'https?://[^"\' <>]+\.(?:mp4|m3u8|webm)[^"\' <>]*', body))][:6], [x.decode() for x in set(re.findall(rb'(?:youtube\.com/embed/|youtu\.be/|vimeo\.com/video/)[\w-]+', body))][:4], len(set(re.findall(rb'/the-presidency/presidential-speeches/[a-z0-9-]+', body))))
    print('== LOC')
    time.sleep(20)
    st, hd, body, _ = req('https://www.loc.gov/film-and-videos/?fo=json&c=10&dates=1984/2004&fa=online-format:video&q=television&at=facets,pagination,results')
    try:
        j = json.loads(body)
        print('  of', (j.get('pagination') or {}).get('of'))
        for f in j.get('facets') or []:
            if f.get('fieldName') in ('partof', 'original-format', 'subject'): print('  facet', f.get('fieldName'), [(x.get('title'), x.get('count')) for x in (f.get('filters') or [])[:25]])
        for r in (j.get('results') or [])[:10]:
            print('   ', r.get('id'), r.get('date'), str(r.get('title'))[:70], r.get('partof'))
        r0 = [r for r in (j.get('results') or []) if 'veterans' not in str(r.get('partof')).lower()][:2]
        for r in r0:
            time.sleep(8)
            ij = jget(r['id'].replace('http://', 'https://').rstrip('/') + '/?fo=json&at=resources,item')
            print('    item', r['id'], json.dumps((ij or {}).get('resources'))[:1200])
    except Exception as e:
        print('  loc fail', st, e, body[:200])
if MODE == 'probe':
    probe(); sys.exit(0)
