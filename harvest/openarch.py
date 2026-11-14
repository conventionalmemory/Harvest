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
MONTHS = {m: i + 1 for i, m in enumerate(['january', 'february', 'march', 'april', 'may', 'june', 'july', 'august', 'september', 'october', 'november', 'december'])}
MONTHS.update({k[:3]: v for k, v in list(MONTHS.items())}); MONTHS['sept'] = 9
def pdate(tx):
    tx = re.sub(r'<[^>]+>', ' ', str(tx or ''))
    m = re.search(r'\b(19[89]\d|200[0-4])-(\d\d)-(\d\d)\b', tx)
    if m and 1 <= int(m.group(2)) <= 12 and 1 <= int(m.group(3)) <= 31: return '%s-%s-%s' % m.groups()
    m = re.search(r'\b(\d{1,2})(?:st|nd|rd|th)?\s+([A-Za-z]{3,9})\.?,?\s+(19[89]\d|200[0-4])\b', tx)
    if m and m.group(2).lower() in MONTHS and 1 <= int(m.group(1)) <= 31: return '%s-%02d-%02d' % (m.group(3), MONTHS[m.group(2).lower()], int(m.group(1)))
    m = re.search(r'\b([A-Za-z]{3,9})\.?\s+(\d{1,2})(?:st|nd|rd|th)?,?\s+(19[89]\d|200[0-4])\b', tx)
    if m and m.group(1).lower() in MONTHS and 1 <= int(m.group(2)) <= 31: return '%s-%02d-%02d' % (m.group(3), MONTHS[m.group(1).lower()], int(m.group(2)))
    m = re.search(r'\b(\d{1,2})/(\d{1,2})/(19[89]\d|200[0-4])\b', tx)
    if m and 1 <= int(m.group(1)) <= 12 and 1 <= int(m.group(2)) <= 31: return '%s-%02d-%02d' % (m.group(3), int(m.group(1)), int(m.group(2)))
    return ''
def inr(d): return bool(d) and '1984-01-01' <= d <= '2004-12-31'
def classify(tx):
    t = tx.lower()
    for ct, rx in (('launch', r'\blaunch|liftoff|lift-off|\blanding\b|countdown'), ('sotu', r'state of the union'), ('inauguration', r'inaugura|swearing[- ]in|oath of office'), ('debate', r'\bdebate'), ('election', r'election night|national convention|campaign|rally|fundrais'), ('hearing', r'hearing|testimony|committee'), ('press', r'press conference|news conference|press briefing|briefing|question[- ]and[- ]answer|interview'), ('mission', r'\bsts[- ]?\d|space shuttle|hubble|\bapollo\b|\bnasa\b|space station|spacewalk|astronaut'), ('speech', r'address|remarks|speech|statement|toast|announc|signing|ceremony|medal|arrival|visit|trip|meeting|summit|tribute|memorial|funeral|eulogy|dinner|reception|lecture|town ?hall|conference|photo')):
        if re.search(rx, t): return ct
    return 'doc'
USX = re.compile(r"(?i)reagan|\bbush\b|clinton|\bgore\b|quayle|mondale|dukakis|perot|\bdole\b|kerry|cheney|white house|state of the union|\bnasa\b|shuttle|\bsts\b|congress|senate|supreme court|pentagon|united states|\bu\.?s\.?\b|american|presidential|first lady|vice president|oval office|camp david|air force|navy|army|marine")
NONUS = re.compile(r"(?i)philippin|arroyo|estrada|malaca|bundestag|duma|knesset|parliament of|lok sabha")
def canon(t):
    t = re.sub(r'^File:', '', t); t = re.sub(r'\.(webm|ogv|ogg|mpg|mpeg|mp4|mov)$', '', t, flags=re.I)
    t = re.sub(r'\s*-\s*NARA\s*-\s*\d+', ' ', t); t = re.sub(r'\(FOIA Case[^)]*\)', ' ', t); t = re.sub(r'^(MT\d+|KSC-[\w-]+)\s+', '', t)
    t = re.sub(r'^Video Recording of\s+', '', t, flags=re.I)
    t = re.sub(r'[_]+', ' ', t); t = re.sub(r'\s+', ' ', t).strip(' -:,.')
    return t.upper()[:80]
def nasa():
    out = []; seen = set(); cands = []
    def page(url):
        j = jget(url, timeout=60)
        its = (j or {}).get('collection', {}).get('items') or []
        for it in its:
            d0 = (it.get('data') or [{}])[0]
            if d0.get('nasa_id') and d0['nasa_id'] not in seen and d0.get('media_type') == 'video':
                seen.add(d0['nasa_id']); cands.append(d0)
        return len(its), ((j or {}).get('collection', {}).get('metadata') or {}).get('total_hits', 0)
    for y in range(1984, 2005):
        for pg in range(1, 40):
            n, tot = page('https://images-api.nasa.gov/search?media_type=video&year_start=%d&year_end=%d&page_size=100&page=%d' % (y, y, pg))
            if pg == 1: print('nasa year', y, 'hits', tot, flush=True)
            if n < 100: break
    QS = ['launch coverage', 'landing coverage', 'launch day activities', 'KSC-198', 'KSC-199', 'KSC-200', 'STS-41', 'STS-51', 'STS-61', 'STS-26', 'STS-27', 'STS-28', 'STS-29', 'STS-30', 'STS-31', 'STS-32', 'STS-33', 'STS-34', 'STS-35', 'STS-36', 'STS-37', 'STS-38', 'STS-39', 'STS-40', 'STS-42', 'STS-43', 'STS-44', 'STS-45', 'STS-46', 'STS-47', 'STS-48', 'STS-49', 'STS-50', 'STS-52', 'STS-53', 'STS-54', 'STS-55', 'STS-56', 'STS-57', 'STS-58', 'STS-59', 'STS-60', 'STS-62', 'STS-63', 'STS-64', 'STS-65', 'STS-66', 'STS-67', 'STS-68', 'STS-69', 'STS-70', 'STS-71', 'STS-72', 'STS-73', 'STS-74', 'STS-75', 'STS-76', 'STS-77', 'STS-78', 'STS-79', 'STS-80', 'STS-81', 'STS-82', 'STS-83', 'STS-84', 'STS-85', 'STS-86', 'STS-87', 'STS-88', 'STS-89', 'STS-90', 'STS-91', 'STS-92', 'STS-93', 'STS-94', 'STS-95', 'STS-96', 'STS-97', 'STS-98', 'STS-99', 'STS-100', 'STS-101', 'STS-102', 'STS-103', 'STS-104', 'STS-105', 'STS-106', 'STS-107', 'STS-108', 'STS-109', 'STS-110', 'STS-111', 'STS-112', 'STS-113', 'Challenger', 'Columbia', 'Hubble', 'Mir', 'Pathfinder', 'Galileo', 'Magellan', 'Ulysses', 'Cassini', 'Discovery', 'Atlantis', 'Endeavour', 'return to flight', 'rollout', 'Titan', 'Delta', 'Atlas', 'post flight', 'crew press conference', 'mission highlights', 'resource reel', 'year in review']
    for q in QS:
        for pg in range(1, 12):
            n, tot = page('https://images-api.nasa.gov/search?q=%s&media_type=video&page_size=100&page=%d' % (urllib.parse.quote(q), pg))
            if n < 100: break
    print('nasa candidates', len(cands), flush=True)
    pre = []
    for d0 in cands:
        tx = ' '.join(str(d0.get(k) or '') for k in ('title', 'nasa_id', 'description'))
        dc = str(d0.get('date_created') or '')[:10]
        ad = dc if inr(dc) and not dc.endswith('-01-01') else ''
        td = pdate(str(d0.get('title') or '') + ' ' + str(d0.get('nasa_id') or ''))
        if inr(td): ad = td
        if not ad and inr(dc): ad = pdate(str(d0.get('description') or ''))
        if not inr(ad): continue
        pre.append((d0, ad))
    print('nasa dated in range', len(pre), flush=True)
    def one(a):
        d0, ad = a
        if left() < 600: return None
        m = jget('https://images-api.nasa.gov/asset/' + urllib.parse.quote(d0['nasa_id']), timeout=40)
        hs = [x['href'] for x in (m or {}).get('collection', {}).get('items', []) if str(x.get('href', '')).lower().endswith('.mp4')]
        by = {}
        for h in hs: by.setdefault(h.rsplit('~', 1)[-1].lower(), h)
        best = None
        for key in ('medium.mp4', 'small.mp4', 'orig.mp4', 'large.mp4', 'mobile.mp4'):
            if key not in by: continue
            u = urllib.parse.quote(by[key].replace('http://', 'https://'), safe=':/~')
            d, st, hd = mp4dur(u)
            if st not in (200, 206) or not d or 'video' not in str(hd.get('content-type')): continue
            m2 = re.search(r'/(\d+)$', hd.get('content-range', '')); size = int(m2.group(1)) if m2 else 0
            mbps = size * 8 / d / 1e6 if size else 0
            if key == 'orig.mp4' and mbps > 8 and ('mobile.mp4' in by or 'large.mp4' in by): continue
            best = (u, d, key, round(mbps, 1)); break
        if not best or best[1] < 300: return ('short' if best else 'nofile', None)
        tx = str(d0.get('title') or '') + ' ' + str(d0.get('description') or '')[:300]
        return ('ok', {'i': 'nasa:' + d0['nasa_id'], 'src': 'nasa', 'q': 'tech', 't': str(d0.get('title') or d0['nasa_id'])[:160], 'k': canon(str(d0.get('title') or d0['nasa_id'])), 'ad': ad, 'u': [[best[0], round(best[1])]], 'lic': 'NASA media, generally not copyrighted (nasa.gov media usage guidelines)', 'ct': classify(tx), 'ds': str(d0.get('description') or '')[:300], 'var': best[2], 'mbps': best[3], 'fmt': 'mp4'})
    st = collections.Counter()
    with ThreadPoolExecutor(8) as ex:
        for r in ex.map(one, pre):
            if not r: st['budget'] += 1; continue
            st[r[0]] += 1
            if r[1]: out.append(r[1])
    print('nasa results', dict(st), flush=True)
    return out
CUA = {'User-Agent': 'ConventionalMemoryHarvest/1.0 (https://github.com/conventionalmemory/harvest)'}
def commons():
    out = []; seen = set(); st = collections.Counter()
    QS = ['deepcategory:"Videos of Ronald Reagan"', 'deepcategory:"Videos of Bill Clinton"', 'deepcategory:"Videos of George H. W. Bush"', 'deepcategory:"Videos of George W. Bush"', 'deepcategory:"Videos of presidential inaugurations of the United States"', 'deepcategory:"Videos by the Ronald Reagan Presidential Library"', 'incategory:"US National Archives Collection WJC-WHTV: Video Recordings of the White House Television Office (Clinton Administration), 1/20/1993 - 1/20/2001"', '"State of the Union"', '"Space Shuttle"', 'STS launch', 'Challenger', 'Hubble', '"press conference"', '"presidential debate"', '"Democratic National Convention"', '"Republican National Convention"', 'inauguration', '"White House"', '"Reagan" address', '"Clinton" remarks', '"Bush" remarks', '"Gore"', '"Thatcher"', '"Gorbachev"', '"Desert Storm"', '"Gulf War"', '"Berlin Wall"', '"Oklahoma City"', '"September 11"', '"Olympics"', 'NASA 1986', 'NASA 1990', 'NASA 1995', 'NASA 1998', 'NASA 2003', '"Mir"', '"International Space Station"', '"Mars Pathfinder"', '"C-SPAN"', '"news conference"', '"radio address"', '"Department of Defense" 1991', '"Air Force" 1990', '"Navy" 1988', 'hurricane 1992', 'earthquake 1989', '"Mount St. Helens"', 'election 1992', 'election 1996', 'election 2000', 'election 1988', 'election 1984', 'election 2004', '"President Reagan"', '"President Clinton"', '"President Bush"', '"Vice President"', '"First Lady"', '"Hillary"', '"Nancy Reagan"', '"Barbara Bush"', '"Pentagon"', '"Senate"', '"Supreme Court"', '"Oval Office"', '"Rose Garden"', '"Camp David"', '"Air Force One"', '"Address to the Nation"', '"radio address" Reagan', '"Reagan-Bush"', '"Clinton-Gore"', '"summit"', '"Geneva"', '"Reykjavik"', '"Moscow"', '"NATO"', '"United Nations"', '"Christmas" White House', '"Thanksgiving" turkey', '"Easter Egg Roll"', '"Medal of Freedom"', '"Medal of Honor"', '"Kennedy Center"', '"Correspondents"', '"Super Bowl" President', '"World Series" President', '"NCAA" President', '"Olympic" President', 'NARA 1984', 'NARA 1985', 'NARA 1986', 'NARA 1987', 'NARA 1988', 'NARA 1989', 'NARA 1990', 'NARA 1991', 'NARA 1992', 'NARA 1993', 'NARA 1994', 'NARA 1995', 'NARA 1996', 'NARA 1997', 'NARA 1998', 'NARA 1999', 'NARA 2000', 'NARA 2001']
    for q in QS:
        if left() < 900: break
        cont = {}
        for pg in range(40):
            url = 'https://commons.wikimedia.org/w/api.php?action=query&format=json&generator=search&gsrnamespace=6&gsrlimit=50&gsrsearch=' + urllib.parse.quote('filetype:video ' + q) + '&prop=videoinfo&viprop=url|size|mime|derivatives|extmetadata&viextmetadatafilter=DateTimeOriginal|LicenseShortName|Artist|Credit|ImageDescription' + ''.join('&%s=%s' % (k, urllib.parse.quote(str(v))) for k, v in cont.items())
            j = jget(url, headers=CUA, timeout=60)
            time.sleep(0.6)
            if not j: st['apifail'] += 1; break
            for p in ((j.get('query') or {}).get('pages') or {}).values():
                if p['title'] in seen or not p.get('videoinfo'): continue
                seen.add(p['title']); st['seen'] += 1
                vi = p['videoinfo'][0]; em = vi.get('extmetadata') or {}
                dur = vi.get('duration') or 0
                if dur < 300: st['short'] += 1; continue
                dv = (em.get('DateTimeOriginal') or {}).get('value', '')
                desc = re.sub(r'<[^>]+>', ' ', (em.get('ImageDescription') or {}).get('value', ''))
                ad = pdate(p['title']) or pdate(dv) or pdate(desc[:400])
                if not inr(ad): st['nodate'] += 1; continue
                if re.search(r'[\u0400-\u04ff\u4e00-\u9fff\u0600-\u06ff]', p['title'] + desc[:200]): st['foreign'] += 1; continue
                ds = [d for d in (vi.get('derivatives') or []) if str(d.get('type', '')).startswith('video/webm')]
                pick = None
                for key in ('480p.vp9.webm', '360p.vp9.webm', '720p.vp9.webm', '240p.vp9.webm'):
                    for d in ds:
                        if d.get('transcodekey') == key or str(d.get('src', '')).endswith(key): pick = d['src']; break
                    if pick: break
                fmt = 'webm'
                if not pick:
                    if vi.get('mime') in ('video/webm', 'video/mp4') and (vi.get('size') or 0) / max(dur, 1) * 8 / 1e6 < 8: pick = vi['url']; fmt = vi['mime'].split('/')[1]
                    else: st['noderiv'] += 1; continue
                tx = p['title'] + ' ' + desc[:300]
                if NONUS.search(tx) or not USX.search(tx): st['nonus'] += 1; continue
                ct = classify(p['title'])
                if ct == 'doc': ct = classify(desc[:200])
                lic = (em.get('LicenseShortName') or {}).get('value', '')
                by = re.sub(r'<[^>]+>', '', (em.get('Artist') or {}).get('value', '') or (em.get('Credit') or {}).get('value', ''))[:120]
                out.append({'i': 'commons:' + p['title'][5:], 'src': 'commons', 'q': 'tech' if ct in ('launch', 'mission') else 'news', 't': re.sub(r'\.(webm|ogv|ogg|mpg|mpeg|mp4|mov)$', '', p['title'][5:], flags=re.I)[:160], 'k': canon(p['title']), 'ad': ad, 'u': [[pick, round(dur)]], 'lic': lic, 'by': by.strip(), 'pg': 'https://commons.wikimedia.org/wiki/' + urllib.parse.quote(p['title'].replace(' ', '_')), 'ct': ct, 'ds': desc.strip()[:300], 'fmt': fmt})
            cont = j.get('continue') or {}
            if not cont: break
        print('commons q', q[:60], 'kept so far', len(out), flush=True)
    def chk(x):
        s2, hd, b, fin = req(x['u'][0][0], rng=(0, 1023), headers=CUA, timeout=30, tries=4)
        x['_ok'] = s2 in (200, 206) and 'video' in str(hd.get('content-type'))
        x['_h'] = (s2, hd.get('content-type'), hd.get('accept-ranges'), hd.get('access-control-allow-origin'))
        return x
    with ThreadPoolExecutor(3) as ex: out = list(ex.map(chk, out))
    for rnd in range(2):
        bad = [x for x in out if not x['_ok']]
        if not bad: break
        time.sleep(30)
        for x in bad: chk(x); time.sleep(1)
    print('commons header samples', [x['_h'] for x in out[:5]])
    bad = [x for x in out if not x['_ok']]
    print('commons url failures', collections.Counter(str(x['_h'][0]) for x in bad).most_common(5))
    out = [x for x in out if x['_ok']]
    for x in out: x.pop('_ok'); x.pop('_h')
    st['urlfail'] = len(bad)
    print('commons results', dict(st), flush=True)
    return out
items = []
for name, fn in (('nasa', nasa), ('commons', commons)):
    if os.environ.get('ONLY') and os.environ['ONLY'] != name: continue
    try: items += fn()
    except Exception as e:
        import traceback; traceback.print_exc(); print('source failed', name, e)
old = []
if os.path.exists(OUT):
    try: old = json.load(gzip.open(OUT, 'rt', encoding='utf-8'))
    except Exception: old = []
got = set(x['src'] for x in items)
by = {x['i']: x for x in old if x.get('src') not in got}
for x in items: by[x['i']] = x
final = sorted(by.values(), key=lambda x: (x['ad'], x['i']))
os.makedirs('catalog', exist_ok=True)
json.dump(final, gzip.open(OUT, 'wt', encoding='utf-8'), ensure_ascii=False, separators=(',', ':'))
hrs = lambda L: round(sum(u[1] for x in L for u in x['u']) / 3600)
print('TOTAL', len(final), 'items', hrs(final), 'hours', 'distinct days', len(set(x['ad'] for x in final)))
for s in sorted(set(x['src'] for x in final)):
    L = [x for x in final if x['src'] == s]; print(' source', s, len(L), 'items', hrs(L), 'h', 'fmt', dict(collections.Counter(x.get('fmt') for x in L)))
print(' per year', sorted(collections.Counter(x['ad'][:4] for x in final).items()))
print(' per ct', collections.Counter(x['ct'] for x in final).most_common())
print(' licenses', collections.Counter(x['lic'][:40] for x in final).most_common(8))
import random
random.seed(7)
for x in random.sample(final, min(60, len(final))): print('  ROW', x['ad'], x['src'], x['ct'], round(x['u'][0][1] / 60), 'min |', x['k'][:60], '|', x['u'][0][0][-60:])
