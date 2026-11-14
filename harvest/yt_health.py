import gzip, json, os, re, sys, time, random, datetime, collections, threading, urllib.request, urllib.parse, urllib.error, concurrent.futures

MODE = os.environ.get('MODE', 'plan')
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PARTS = os.path.join(ROOT, 'parts')
USED = os.path.join(ROOT, 'catalog', 'yt_used.txt.gz')
OUT = os.path.join(ROOT, 'catalog', 'yt_health.json.gz')
PLAN = os.path.join(PARTS, 'yth_plan.json.gz')
UA = 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36'
REF = 'https://example.com/'
GOOD = ['dQw4w9WgXcQ', 'jNQXAC9IVRw', '9bZkp7q19f0', 'aqz-KE-bpKQ']
MISSING = ['aaaaaaaaaaE', 'zzzzzzzzzz0']
T0 = time.time()
BUDGET = float(os.environ.get('BUDGET_MIN', '100')) * 60
GAP = float(os.environ.get('GAP', '0.3'))
THREADS = int(os.environ.get('THREADS', '3'))
STAT = collections.Counter()
LOCK = threading.Lock()
NEXT = [0.0]
HOLD = [0.0]
USE_EMBED = [True]
DEC = json.JSONDecoder()
GONE = {'private': 'private', 'terminated': 'account terminated', 'copyright': 'removed on a copyright claim', 'uploader': 'removed by the uploader', 'policy': 'removed for a policy violation', 'unavailable': 'unavailable'}
LIMITED = {'age': 'age-restricted', 'region': 'not available in this country', 'members': 'members only', 'paid': 'paid content', 'login': 'sign-in required', 'claim': 'blocked on a copyright claim', 'warning': 'content warning before playback'}
OLD = os.path.join(PARTS, 'old')


def left():
    return BUDGET - (time.time() - T0)


def wait():
    with LOCK:
        t = max(time.time(), NEXT[0], HOLD[0])
        NEXT[0] = t + GAP * (0.7 + random.random() * 0.6)
    d = t - time.time()
    if d > 0: time.sleep(d)


def slow(sec):
    with LOCK:
        HOLD[0] = max(HOLD[0], time.time() + sec)
        STAT['slowdowns'] += 1


def fetch(url, ref=False, timeout=25, data=None, extra=None):
    wait()
    h = {'User-Agent': UA, 'Accept-Language': 'en-US,en;q=0.9', 'Accept-Encoding': 'gzip', 'Cookie': 'CONSENT=YES+1; SOCS=CAI'}
    if ref: h['Referer'] = REF
    if extra: h.update(extra)
    try:
        with urllib.request.urlopen(urllib.request.Request(url, data=data, headers=h), timeout=timeout) as r:
            b = r.read()
            if (r.headers.get('Content-Encoding') or '').lower() == 'gzip': b = gzip.decompress(b)
            return r.status, b.decode('utf-8', 'replace'), r.geturl() or ''
    except urllib.error.HTTPError as e:
        try:
            b = e.read()
            if (e.headers.get('Content-Encoding') or '').lower() == 'gzip': b = gzip.decompress(b)
            b = b.decode('utf-8', 'replace')
        except Exception:
            b = ''
        return e.code, b, e.geturl() or ''
    except Exception as e:
        return 0, str(e)[:80], ''


def pause(a, code):
    if code == 429: slow(20 + 25 * a)
    time.sleep(2 + a * a * 4 + random.random() * 3)


def oembed(vid):
    u = 'https://www.youtube.com/oembed?format=json&url=' + urllib.parse.quote('https://www.youtube.com/watch?v=' + vid, safe='')
    last = 'error'
    for a in range(5):
        if a and left() < 60: break
        code, body, fin = fetch(u)
        here = 'youtube.com/oembed' in fin
        if code == 200 and here:
            try:
                j = json.loads(body)
                if isinstance(j, dict) and j.get('html'):
                    with LOCK: STAT['oembed_200'] += 1
                    return 200, ''
            except Exception:
                pass
            last = 'unreadable answer'
        elif code in (400, 401, 403, 404) and here and len(body) < 300 and '<html' not in body.lower():
            with LOCK: STAT['oembed_%d' % code] += 1
            return code, ''
        else:
            last = 'rate limited' if code == 429 else 'http %d' % code if code else 'network error'
            if not here and fin: last = 'redirected'
        with LOCK: STAT['oembed_retry'] += 1
        pause(a, code)
    with LOCK: STAT['oembed_fail'] += 1
    return 0, last


def texts(o, out):
    if isinstance(o, dict):
        for k, v in o.items():
            if k in ('text', 'simpleText', 'content', 'reason', 'subreason') and isinstance(v, str):
                if v.strip() and not v.startswith('http'): out.append(v.strip())
            else:
                texts(v, out)
    elif isinstance(o, list):
        for v in o: texts(v, out)
    return out


def parse(html):
    ps = None
    k = '"embedded_player_response":'
    i = html.find(k)
    if i >= 0:
        j = i + len(k)
        while j < len(html) and html[j] in ' \n\t': j += 1
        try:
            s, _ = DEC.raw_decode(html, j)
            d = json.loads(s) if isinstance(s, str) else s
            if isinstance(d, dict): ps = d.get('previewPlayabilityStatus') or d.get('playabilityStatus')
        except Exception:
            ps = None
    if not isinstance(ps, dict) or not ps.get('status'):
        f = html.replace('\\\\', '\\').replace('\\"', '"').replace('\\x22', '"')
        m = re.search(r'"(?:previewP|p)layabilityStatus":\s*\{"status":\s*"([A-Z_]+)"', f)
        if not m: return None
        seg = f[m.start():m.start() + 4000]
        ps = {'status': m.group(1), 'errorScreen': {'runs': [{'text': x} for x in re.findall(r'"(?:text|simpleText|reason)":\s*"([^"]{1,300})"', seg)]}}
        e = re.search(r'"playableInEmbed":\s*(true|false)', seg)
        if e: ps['playableInEmbed'] = e.group(1) == 'true'
    seen = []
    raw = [ps['reason']] if isinstance(ps.get('reason'), str) else texts(ps.get('reason'), [])
    for t in raw + texts(ps.get('errorScreen'), []) + texts(ps.get('messages'), []):
        t = re.sub(r'\s+', ' ', re.sub(r'<[^>]+>', ' ', t)).strip()
        if t and t not in seen: seen.append(t)
    g = re.search(r'"GL":\s*"([A-Z]{2})"', html)
    r = {'st': str(ps.get('status')), 'emb': ps.get('playableInEmbed'), 'why': ' / '.join(seen)[:200], 'gl': g.group(1) if g else ''}
    if ps.get('desktopLegacyAgeGateReason') or 'AGE' in r['st']: r['why'] = (r['why'] + ' / age gate').strip(' /')
    if 'CONTENT_CHECK' in r['st']: r['why'] = (r['why'] + ' / content_check').strip(' /')
    return r


def embed(vid, host='www.youtube.com'):
    for a in range(4):
        if a and left() < 60: break
        code, body, fin = fetch('https://' + host + '/embed/' + vid, ref=True)
        if code == 200 and '/embed/' in fin and 'youtube' in fin:
            r = parse(body)
            if r:
                with LOCK: STAT['embed_read'] += 1
                return r
            with LOCK: STAT['embed_nostatus'] += 1
            if a >= 1: break
        elif code in (404, 410) and '/embed/' in fin and 'youtube' in fin:
            with LOCK: STAT['embed_%d' % code] += 1
            return {'st': 'HTTP%d' % code, 'emb': None, 'why': 'This video is unavailable', 'gl': ''}
        with LOCK: STAT['embed_retry'] += 1
        pause(a, code)
    with LOCK: STAT['embed_fail'] += 1
    return None


def kind(w):
    w = (w or '').lower()
    if 'not a bot' in w or 'unusual traffic' in w or 'automated' in w or 'configuration error' in w or 'error 153' in w: return 'bot'
    if 'private' in w: return 'private'
    if 'terminated' in w or ('account' in w and 'closed' in w): return 'terminated'
    if 'country' in w or 'your location' in w or 'region' in w: return 'region'
    if 'blocked' in w and ('claim' in w or 'copyright' in w) and 'this website' not in w: return 'claim'
    if 'copyright' in w: return 'copyright'
    if 'viewer discretion' in w or 'self-harm' in w or 'content_check' in w: return 'warning'
    if 'removed by the uploader' in w or 'removed by the user' in w: return 'uploader'
    if 'violat' in w or 'terms of service' in w or 'community guidelines' in w or 'harassment' in w or 'hate speech' in w: return 'policy'
    if re.search(r'\bage\b|age-restricted|age gate|inappropriate', w): return 'age'
    if 'member' in w or 'join this channel' in w: return 'members'
    if 'payment' in w or 'purchase' in w or 'rental' in w: return 'paid'
    if 'other websites' in w or 'this website' in w or 'watch on youtube' in w or 'embed' in w: return 'embed'
    if 'unavailable' in w or 'no longer available' in w or "isn't available" in w or 'not available' in w or 'removed' in w or 'does not exist' in w: return 'unavailable'
    if 'sign in' in w or 'log in' in w: return 'login'
    return ''


def owner(em):
    m = re.search(r'claimed content by (.{1,60}?)\.?(?: /|$)|content from (.{1,60}?), who has blocked', em['why'] if em else '')
    return ' (%s)' % (m.group(1) or m.group(2)) if m else ''


def judge(oe, note, em):
    k = kind(em['why']) if em else ''
    if k == 'bot':
        em = None; k = ''
        with LOCK: STAT['embed_botcheck'] += 1
    st = em['st'] if em else ''
    tail = ' | oembed %s' % (oe or note)
    if em: tail += ' | embed ' + st + (': ' + em['why'][:110] if em['why'] and st != 'OK' else '')
    else: tail += ' | embed page not read'
    if oe == 0: return 'unknown', 'no answer' + tail
    if oe in (400, 404): return 'gone', GONE.get(k, 'not found') + tail
    if oe in (401, 403):
        if k in GONE and k != 'unavailable': return 'gone', GONE[k] + tail
        if k in LIMITED: return 'restricted', LIMITED[k] + owner(em) + tail
        return 'noembed', 'embedding disabled' + tail
    if not em: return 'ok', 'embeddable' + tail
    if st == 'OK' and em['emb'] is not False: return 'ok', 'playable' + tail
    if k in LIMITED: return 'restricted', LIMITED[k] + owner(em) + tail
    if k == 'embed' or em['emb'] is False:
        m = re.search(r'content from (.{1,60}?), who has blocked it from display', em['why'])
        return 'noembed', ('embedding blocked by the content owner (%s)' % m.group(1) if m else 'not playable in embeds') + tail
    if k in GONE: return 'restricted', 'unavailable in the embedded player' + tail
    return 'restricted', 'not playable' + tail


def observe(vid):
    try:
        oe, note = oembed(vid)
        em = embed(vid) if USE_EMBED[0] and left() > 30 else None
        s, r = judge(oe, note, em)
        return {'s': s, 'r': r, 'oe': oe, 'em': em['st'] if em else '', 'gl': em['gl'] if em else ''}
    except Exception as e:
        with LOCK: STAT['checker_error'] += 1
        return {'s': 'unknown', 'r': 'no answer | checker error ' + type(e).__name__, 'oe': 0, 'em': '', 'gl': ''}


def settle(obs):
    d = [o for o in obs if o['s'] != 'unknown']
    if not d: return None
    ss = [o['s'] for o in d]
    if set(ss) == {'ok'}: return d[-1]
    if len(set(ss)) == 1 and len(ss) >= 2: return d[-1]
    if len(ss) >= 3 and len(set(ss[-3:])) == 1: return d[-1]
    return None


def canary():
    v = random.choice(GOOD)
    for a in range(6):
        oe, note = oembed(v)
        em = embed(v) if USE_EMBED[0] and oe == 200 else None
        if oe == 200 and (not USE_EMBED[0] or (em and em['st'] == 'OK' and em['emb'] is not False)): return True
        with LOCK: STAT['canary_miss'] += 1
        if left() < 120: return False
        slow(30 + 30 * a); time.sleep(5)
        v = random.choice(GOOD)
    return False


def setup():
    oks = 0; embs = 0
    for v in GOOD:
        oe, note = oembed(v); em = embed(v)
        print('  known good', v, 'oembed', oe or note, 'embed', em, flush=True)
        if oe == 200: oks += 1
        if em and em['st'] == 'OK' and kind(em['why']) != 'bot': embs += 1
    USE_EMBED[0] = embs * 2 >= len(GOOD)
    print('oembed usable', oks, 'of', len(GOOD), '| embed page usable', USE_EMBED[0], flush=True)
    return oks * 2 >= len(GOOD)


def sweep(ids, obs, label, step):
    blocked = False
    with concurrent.futures.ThreadPoolExecutor(THREADS) as ex:
        for i in range(0, len(ids), step):
            part = ids[i:i + step]
            if left() < 90 or blocked:
                for v in part: obs[v].append({'s': 'unknown', 'r': 'not checked: ' + ('checker blocked' if blocked else 'out of time'), 'oe': 0, 'em': '', 'gl': ''})
                continue
            if not canary():
                blocked = True
                print(label, 'known-good check failed at', i, flush=True)
                for v in part: obs[v].append({'s': 'unknown', 'r': 'not checked: checker blocked', 'oe': 0, 'em': '', 'gl': ''})
                continue
            for v, o in zip(part, ex.map(observe, part)): obs[v].append(o)
            if (i // step) % 5 == 0: print(label, min(i + step, len(ids)), '/', len(ids), 'min', round((time.time() - T0) / 60, 1), dict(STAT), flush=True)
    return not blocked


def final(obs):
    f = settle(obs)
    if f: return dict(f, n=len(obs))
    ss = '/'.join(o['s'] for o in obs)
    d = [o for o in obs if o['s'] != 'unknown']
    if d: return {'s': 'unknown', 'r': 'inconsistent answers (%s) | last: %s' % (ss, d[-1]['r']), 'oe': d[-1]['oe'], 'em': d[-1]['em'], 'gl': d[-1]['gl'], 'n': len(obs)}
    return dict(obs[-1], n=len(obs)) if obs else {'s': 'unknown', 'r': 'not checked', 'oe': 0, 'em': '', 'gl': '', 'n': 0}


def rounds(ids, label, first=120, maxobs=5):
    obs = {v: [] for v in ids}
    sweep(ids, obs, label + ' pass 1', first)
    for n in range(2, maxobs + 1):
        todo = [v for v in ids if settle(obs[v]) is None and not obs[v][-1]['r'].startswith('not checked')]
        if not todo or left() < 120: break
        print(label, 'pass', n, 'rechecking', len(todo), collections.Counter(obs[v][-1]['s'] for v in todo).most_common(), flush=True)
        time.sleep(min(45, max(5, left() - 120)))
        sweep(todo, obs, label + ' pass %d' % n, 40)
    return {v: final(obs[v]) for v in ids}


def table(res, title):
    print('==', title, len(res))
    c = collections.Counter(r['s'] for r in res.values())
    for s in ('ok', 'noembed', 'gone', 'restricted', 'unknown'): print('  %-10s %6d  %5.1f%%' % (s, c.get(s, 0), 100.0 * c.get(s, 0) / max(1, len(res))))
    print('== by reason')
    c = collections.Counter((r['s'], r['r'].split(' | ')[0]) for r in res.values())
    for (s, w), n in sorted(c.items(), key=lambda x: (-x[1], x[0])): print('  %-10s %6d  %s' % (s, n, w))
    print('== oembed answer x embed page status')
    c = collections.Counter((r.get('oe', 0), r.get('em', '') or '-') for r in res.values())
    for (a, b), n in sorted(c.items(), key=lambda x: (-x[1], str(x[0]))): print('  %-4s %-28s %6d' % (a, b, n))
    c = collections.Counter(r.get('gl', '') or '-' for r in res.values())
    print('== country seen by the embed page', c.most_common(8))
    c = collections.Counter(re.sub(r'^.*?\| embed ', '', r['r'])[:120] for r in res.values() if r['s'] != 'ok' and '| embed ' in r['r'])
    print('== embed page messages for ids that are not ok')
    for w, n in c.most_common(40): print('  %6d  %s' % (n, w))
    sys.stdout.flush()


def hosts(ids):
    same = collections.Counter(); diff = []

    def both(v):
        return v, embed(v), embed(v, 'www.youtube-nocookie.com')

    with concurrent.futures.ThreadPoolExecutor(THREADS) as ex:
        for v, a, b in ex.map(both, ids):
            if left() < 120: break
            if not a or not b: same['not read'] += 1; continue
            ka = (a['st'], a['emb']); kb = (b['st'], b['emb'])
            same['same ' + a['st'] if ka == kb else 'different'] += 1
            if ka != kb and len(diff) < 30: diff.append((v, a['st'], a['why'][:70], b['st'], b['why'][:70]))
    print('== embed page on the main host against the privacy-enhanced host', len(ids), sorted(same.items(), key=lambda x: -x[1]))
    for x in diff: print('  differs', x)
    sys.stdout.flush()


def load_used(prev):
    ids = []
    for line in gzip.open(USED, 'rt', encoding='utf-8'):
        v = line.strip()
        if re.fullmatch(r'[A-Za-z0-9_-]{11}', v): ids.append(v)
        elif v: print('skipped malformed id', repr(v[:20]))
    have = set(ids)
    kept = [v for v, r in prev.items() if r and r[0] != 'ok' and v not in have]
    if kept: print('ids no longer in the list but not ok in the last result, still tracked', len(kept))
    return sorted(have | set(kept))


def load_prev():
    try:
        return json.load(gzip.open(OUT, 'rt', encoding='utf-8')).get('ids') or {}
    except Exception:
        return {}


def probe(sample):
    print('== known good and never-used ids')
    for v in GOOD + MISSING + sample:
        u = 'https://www.youtube.com/oembed?format=json&url=' + urllib.parse.quote('https://www.youtube.com/watch?v=' + v, safe='')
        code, body, fin = fetch(u)
        print('  oembed', v, code, repr(body[:70]), fin[:60])
        code, body, fin = fetch('https://www.youtube.com/embed/' + v, ref=True)
        r = parse(body) if code == 200 else None
        print('  embed ', v, code, len(body), fin[:50], r)
        if code == 200 and (not r or r['st'] != 'OK'):
            for mk in ('previewPlayabilityStatus', 'playabilityStatus', 'embedded_player_response', 'errorScreen'):
                i = body.find(mk)
                print('    marker', mk, i, repr(body[max(0, i - 40):i + 700]) if i >= 0 and mk != 'embedded_player_response' else '')
                if i >= 0 and mk != 'embedded_player_response': break
    print('== embed page without a referring page')
    for v in GOOD[:2]:
        code, body, fin = fetch('https://www.youtube.com/embed/' + v)
        print('  embed ', v, code, len(body), parse(body) if code == 200 else None)
    print('== player endpoint (embedded client)')
    for v in GOOD[:2]:
        b = {'videoId': v, 'context': {'client': {'clientName': 'WEB_EMBEDDED_PLAYER', 'clientVersion': '1.20240723.01.00', 'hl': 'en', 'gl': 'US'}, 'thirdParty': {'embedUrl': REF}}}
        code, body, fin = fetch('https://www.youtube.com/youtubei/v1/player?prettyPrint=false', data=json.dumps(b).encode(), extra={'Content-Type': 'application/json', 'Origin': 'https://www.youtube.com'})
        try: ps = json.loads(body).get('playabilityStatus') or {}
        except Exception: ps = {}
        print('  player', v, code, ps.get('status'), repr(str(ps.get('reason'))[:80]), ps.get('playableInEmbed'))
    print('requests', dict(STAT), flush=True)


def listed():
    ids = [v for v in re.split(r'[\s,]+', os.environ.get('IDS', '')) if re.fullmatch(r'[A-Za-z0-9_-]{11}', v)]
    by = collections.defaultdict(list)
    if os.path.isdir(OLD):
        for fn in sorted(os.listdir(OLD)):
            try: d = json.load(gzip.open(os.path.join(OLD, fn), 'rt', encoding='utf-8'))
            except Exception: continue
            for r in d if isinstance(d, list) else []:
                oe = (r.get('m') or {}).get('oe', r.get('oe')) if isinstance(r, dict) else None
                v = r.get('vid') if isinstance(r, dict) else None
                if v and oe in (400, 401, 403, 404) and re.fullmatch(r'[A-Za-z0-9_-]{11}', v): by[oe].append(v)
        print('earlier lookups: ids not embeddable then', {k: len(set(L)) for k, L in by.items()})
        random.seed(5)
        for k in sorted(by):
            L = sorted(set(by[k])); random.shuffle(L); ids += L[:250]
    return sorted(set(ids))


def plan():
    os.makedirs(PARTS, exist_ok=True)
    prev = load_prev()
    ids = load_used(prev)
    total = len(ids)
    scope = os.environ.get('SCOPE', 'all').strip() or 'all'
    L = listed()
    if (os.environ.get('IDS', '').strip() or os.environ.get('FROM_RUN', '').strip() or scope == 'list') and not L:
        print('nothing to check in the given list'); sys.exit(1)
    have = set(ids)
    extra = [v for v in L if v not in have]
    if scope == 'list':
        ids = []
    elif scope == 'recheck':
        ids = [v for v in ids if (prev.get(v) or ['new'])[0] != 'ok']
    lim = int(os.environ.get('LIMIT', '0') or 0)
    if lim and len(ids) > lim:
        st = len(ids) / float(lim)
        ids = [ids[int(i * st)] for i in range(lim)]
    print('ids in list', total, '| previous result', len(prev), '| scope', scope, '| to check', len(ids), '| listed ids checked on the side', len(extra), flush=True)
    ids = sorted(set(ids) | set(extra))
    random.seed(7)
    probe(random.sample(ids, min(10, len(ids))))
    json.dump({'ids': ids, 'scope': scope, 'total': total, 'extra': extra}, gzip.open(PLAN, 'wt', encoding='utf-8'))


def check():
    S = int(os.environ.get('SHARD', '0')); N = int(os.environ.get('SHARDS', '1'))
    ids = [v for i, v in enumerate(json.load(gzip.open(PLAN, 'rt', encoding='utf-8'))['ids']) if i % N == S]
    random.seed(1000 + S); random.shuffle(ids)
    print('shard', S, 'ids', len(ids), flush=True)
    path = os.path.join(PARTS, 'yth-%d.json.gz' % S)
    if not setup():
        res = {v: {'s': 'unknown', 'r': 'not checked: checker blocked', 'oe': 0, 'em': '', 'gl': '', 'n': 0} for v in ids}
    else:
        res = rounds(ids, 'shard %d' % S)
    json.dump(res, gzip.open(path, 'wt', encoding='utf-8'))
    table(res, 'shard %d' % S)
    print('requests', dict(STAT), 'minutes', round((time.time() - T0) / 60, 1))


def merge():
    P = json.load(gzip.open(PLAN, 'rt', encoding='utf-8'))
    ids = P['ids']
    res = {}
    for fn in sorted(os.listdir(PARTS)):
        if re.fullmatch(r'yth-\d+\.json\.gz', fn):
            d = json.load(gzip.open(os.path.join(PARTS, fn), 'rt', encoding='utf-8'))
            print('part', fn, len(d)); res.update(d)
    miss = [v for v in ids if v not in res]
    print('planned', len(ids), 'answered', len(res), 'missing', len(miss), flush=True)
    table({v: res[v] for v in ids if v in res}, 'shard results')
    usable = setup()
    again = [v for v in ids if v in res and (res[v]['s'] != 'ok' or 'not read' in res[v]['r'])]
    again.sort(key=lambda v: (res[v]['s'] == 'unknown', v))
    cross = collections.Counter()
    if usable and miss:
        print('checking ids no shard answered', len(miss), flush=True)
        res.update(rounds(miss, 'missing'))
    for v in miss:
        if v not in res: res[v] = {'s': 'unknown', 'r': 'not checked', 'oe': 0, 'em': '', 'gl': '', 'n': 0}
    if usable and again:
        print('second opinion from this runner for', len(again), collections.Counter(res[v]['s'] for v in again).most_common(), flush=True)
        obs = {v: [] for v in again}

        def more(v):
            a = res[v]; ob = obs[v]
            d = [o['s'] for o in ob if o['s'] != 'unknown']
            if ob and ob[-1]['r'].startswith('not checked'): return False
            if a['s'] in ('unknown', 'ok'): return settle(ob) is None and len(ob) < 4
            if not d: return len(ob) < 2
            if all(x == a['s'] for x in d) and len(d) >= 1: return False
            return len(ob) < 3

        todo = again
        for n in range(1, 5):
            if not todo or left() < 120: break
            if n > 1:
                print('second opinion pass', n, len(todo), flush=True)
                time.sleep(30)
            sweep(todo, obs, 'second opinion pass %d' % n, 60 if n == 1 else 40)
            todo = [v for v in again if more(v)]
        for v in again:
            a = res[v]; ob = obs[v]
            d = [o for o in ob if o['s'] != 'unknown']
            ss = '/'.join(o['s'] for o in d) or 'none'
            if a['s'] == 'unknown':
                f = settle(ob)
                if f:
                    cross['unknown settled as ' + f['s']] += 1
                    res[v] = dict(f, n=a.get('n', 0) + len(ob))
                elif d:
                    cross['unknown stays, answers ' + ss] += 1
                    res[v] = {'s': 'unknown', 'r': 'inconsistent answers (%s) | last: %s' % (ss, d[-1]['r']), 'oe': d[-1]['oe'], 'em': d[-1]['em'], 'gl': d[-1]['gl'], 'n': a.get('n', 0) + len(ob)}
                else:
                    cross['unknown stays, no answer'] += 1
            elif a['s'] == 'ok':
                f = settle(ob)
                if f and f['s'] == 'ok':
                    cross['ok, embed page %s on the second runner' % ('still not read' if 'not read' in f['r'] else 'read')] += 1
                    res[v] = dict(f, n=a.get('n', 0) + len(ob))
                elif f and f['oe'] == 200:
                    cross['ok changed to %s by the embed page' % f['s']] += 1
                    res[v] = dict(f, n=a.get('n', 0) + len(ob))
                elif d:
                    cross['runners disagree: first ok, second ' + ss] += 1
                    res[v] = {'s': 'unknown', 'r': 'inconsistent answers (first runner ok, second runner %s) | first: %s' % (ss, a['r']), 'oe': a.get('oe', 0), 'em': a.get('em', ''), 'gl': a.get('gl', ''), 'n': a.get('n', 0) + len(ob)}
                else:
                    cross['ok, embed page still not read'] += 1
            elif not d:
                cross['second opinion missing, kept ' + a['s']] += 1
            elif all(o['s'] == a['s'] for o in d):
                cross['confirmed ' + a['s']] += 1
                o = d[-1]
                if 'not read' in a['r'] and 'not read' not in o['r']: a['r'] = o['r']; a['em'] = o['em']; a['gl'] = o['gl']
                a['n'] = a.get('n', 0) + len(ob)
            else:
                cross['runners disagree: first %s, second %s' % (a['s'], ss)] += 1
                res[v] = {'s': 'unknown', 'r': 'inconsistent answers (first runner %s, second runner %s) | first: %s' % (a['s'], ss, a['r']), 'oe': a.get('oe', 0), 'em': a.get('em', ''), 'gl': a.get('gl', ''), 'n': a.get('n', 0) + len(ob)}
    else:
        print('no second opinion:', 'nothing to recheck' if usable else 'this runner cannot reach the service', len(again))
    print('== second opinion', sorted(cross.items(), key=lambda x: -x[1]))
    prev = load_prev()
    used = load_used(prev)
    if usable and USE_EMBED[0]:
        random.seed(13)
        oks = sorted(v for v in used if (res.get(v) or {'s': (prev.get(v) or [''])[0]})['s'] == 'ok')
        bads = [v for v in ids if res[v]['s'] != 'ok' and res[v].get('oe') == 200]
        hosts(random.sample(oks, min(150, len(oks))) + bads[:250])
    extra = [v for v in P.get('extra') or [] if v in res]
    if extra:
        table({v: res[v] for v in extra}, 'listed ids, checked on the side and not written')
        for v in sorted(extra, key=lambda v: (res[v]['s'], res[v]['r'], v))[:900]: print('  %-10s %s  %s' % (res[v]['s'], v, res[v]['r'][:190]))
    if P.get('scope') == 'list': return
    out = {}
    kept = 0
    for v in used:
        if v in res: out[v] = [res[v]['s'], res[v]['r']]
        elif v in prev: out[v] = prev[v]; kept += 1
    full = {v: (res[v] if v in res else {'s': out[v][0], 'r': out[v][1], 'oe': '', 'em': 'earlier run'}) for v in out}
    print('ids in list', len(used), '| in result', len(out), '| carried over from the earlier result', kept, '| not covered', len(used) - len(out))
    table(full, 'final')
    random.seed(11)
    print('== samples')
    for s in ('ok', 'noembed', 'gone', 'restricted', 'unknown'):
        L = sorted(v for v in out if out[v][0] == s)
        for v in random.sample(L, min(25, len(L))): print('  %-10s %s  %s' % (s, v, out[v][1][:150]))
    now = datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
    with gzip.open(OUT, 'wt', encoding='utf-8') as f:
        json.dump({'checked': now, 'ids': out}, f, separators=(',', ':'), sort_keys=True)
    print('wrote', OUT.replace(ROOT + os.sep, ''), len(out), 'checked', now, 'requests', dict(STAT), 'minutes', round((time.time() - T0) / 60, 1))


if __name__ == '__main__':
    {'plan': plan, 'check': check, 'merge': merge}[MODE]()
