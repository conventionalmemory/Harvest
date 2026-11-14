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
    j = jget('https://images-api.nasa.gov/search?q=STS-31%20launch&media_type=video&year_start=1984&year_end=2004&page_size=5')
    print(json.dumps(j)[:1500] if j else 'NASA search failed')
    for it in ((j or {}).get('collection', {}).get('items') or [])[:5]:
        d0 = it['data'][0]
        a = jget('https://images-api.nasa.gov/asset/' + urllib.parse.quote(d0['nasa_id']))
        hs = [x['href'] for x in (a or {}).get('collection', {}).get('items', [])]
        print(' ', d0['nasa_id'], d0.get('date_created'), d0.get('title'), [h.rsplit('~', 1)[-1] for h in hs])
        v = [h for h in hs if h.lower().endswith('.mp4')]
        if v: show('nasa', v[0].replace(' ', '%20').replace('http://', 'https://'), d0.get('title', ''))
    print('== LOC')
    for u in ('https://www.loc.gov/film-and-videos/?fo=json&c=5&dates=1984/2004&fa=online-format:video', 'https://www.loc.gov/search/?fo=json&c=5&q=television+broadcast&fa=online-format:video&dates=1984/2004'):
        st, hd, body, _ = req(u)
        print(' ', u, st, hd.get('content-type'), len(body))
        try: j = json.loads(body)
        except Exception: j = None; print(body[:300])
        if not j: continue
        print('  pagination', json.dumps(j.get('pagination'))[:300])
        for r in (j.get('results') or [])[:5]:
            print('  ', r.get('id'), r.get('date'), r.get('title'), r.get('online_format'), r.get('partof'))
            ij = jget(r['id'].rstrip('/') + '/?fo=json') if str(r.get('id', '')).startswith('http') else None
            if ij:
                res = ij.get('resources') or []
                print('    resources', json.dumps(res)[:900])
                print('    item keys', sorted((ij.get('item') or {}).keys())[:60])
                fl = [f.get('url') for rr in res for g in (rr.get('files') or []) for f in (g if isinstance(g, list) else [g]) if isinstance(f, dict) and str(f.get('url', '')).lower().endswith('.mp4')]
                if fl: show('loc', fl[0], str(r.get('title')))
            time.sleep(3)
    print('== AAPB')
    j = jget('https://americanarchive.org/api.json?q=macneil+lehrer+newshour&fq=access_types:online&rows=5&fl=id,title,xml')
    print(json.dumps(j)[:1200] if j else 'AAPB api failed')
    for d in ((j or {}).get('response', {}).get('docs') or [])[:5]:
        i = d.get('id')
        for u in ('https://americanarchive.org/media/%s?part=1' % i,):
            st, hd, body, fin = req(u, rng=(0, 2047), headers={'Referer': 'https://americanarchive.org/catalog/%s' % i})
            print('  aapb media', i, st, hd.get('content-type'), hd.get('accept-ranges'), fin[:160], hd.get('error'))
            st, hd, body, fin = req(u, rng=(0, 2047))
            print('  aapb media noref', i, st, hd.get('content-type'), fin[:160])
    print('== NARA')
    for u in ('https://catalog.archives.gov/proxy/records/search?q=space%20shuttle%20launch&typeOfMaterials=Moving%20Images&availableOnline=true&limit=5', 'https://catalog.archives.gov/api/v2/records/search?q=space%20shuttle%20launch&limit=5', 'https://catalog.archives.gov/proxy/records/search?q=state%20of%20the%20union&levelOfDescription=item&objectType=Video&limit=5'):
        st, hd, body, _ = req(u)
        print(' ', u, st, hd.get('content-type'), body[:1500].decode('utf-8', 'replace'))
        try:
            j = json.loads(body)
            hits = (j.get('body') or {}).get('hits', {}).get('hits', [])
            for h in hits[:5]:
                rec = h.get('_source', {}).get('record', {})
                objs = rec.get('digitalObjects') or []
                print('   rec', rec.get('naId'), rec.get('title'), rec.get('productionDates') or rec.get('coverageStartDate') or rec.get('broadcastDates'), [(o.get('objectType'), o.get('objectUrl')) for o in objs[:4]])
                v = [o.get('objectUrl') for o in objs if str(o.get('objectUrl', '')).lower().endswith('.mp4')]
                if v: show('nara', v[0], str(rec.get('title')))
        except Exception as e:
            print('   parse', e)
    print('== CSPAN')
    st, hd, body, fin = req('https://www.c-span.org/video/?c=1&q=state+of+the+union+1996')
    print('  cspan', st, hd.get('content-type'), len(body), fin[:120], re.findall(rb'https?://[^"\' ]+\.(?:mp4|m3u8)[^"\' ]*', body)[:5])
    print('== MILLER')
    st, hd, body, fin = req('https://api.millercenter.org/speeches', method='POST', data=b'{}', headers={'Content-Type': 'application/json'})
    print('  miller', st, hd.get('content-type'), body[:700].decode('utf-8', 'replace'))
    st, hd, body, fin = req('https://millercenter.org/the-presidency/presidential-speeches/january-23-1996-state-union-address')
    print('  miller page', st, len(body), [x.decode() for x in set(re.findall(rb'https?://[^"\' <>]+\.(?:mp4|m3u8|mp3)[^"\' <>]*', body))][:8])
    print('== REAGAN/CLINTON/BUSH')
    for u in ('https://www.reaganlibrary.gov/archives/speech/address-nation-explosion-space-shuttle-challenger', 'https://www.clintonlibrary.gov/research/video-and-audio', 'https://bush41library.tamu.edu/audiovisual/videos'):
        st, hd, body, fin = req(u)
        print(' ', u, st, len(body), [x.decode() for x in set(re.findall(rb'https?://[^"\' <>]+\.(?:mp4|m3u8)[^"\' <>]*', body))][:6], [x.decode() for x in set(re.findall(rb'(?:youtube\.com/embed/|youtu\.be/)[\w-]+', body))][:4])
if MODE == 'probe':
    probe(); sys.exit(0)
