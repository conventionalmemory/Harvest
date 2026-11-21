import gzip, json, os, re, sys, time, random
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import yt_needs as Y
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, 'catalog', 'yt_eventfill.json.gz')
def yz(a, s): return {a + i: d for i, d in enumerate(s.split())}
def ordn(n): return str(n) + ('th' if 10 <= n % 100 <= 20 else {1: 'st', 2: 'nd', 3: 'rd'}.get(n % 10, 'th'))
EV = [
 dict(k='oscars', rx=r'academy awards|oscars?\b', q='block', net=lambda y: 'abc', o=1928, md=50, names=['Academy Awards', 'Oscars'], d=yz(1984, '04-09 03-25 03-24 03-30 04-11 03-29 03-26 03-25 03-30 03-29 03-21 03-27 03-25 03-24 03-23 03-21 03-26 03-25 03-24 03-23 02-29')),
 dict(k='grammys', rx=r'grammy', q='block', net=lambda y: 'cbs', o=1958, md=50, names=['Grammy Awards', 'Grammys'], d=yz(1984, '02-28 02-26 02-25 02-24 03-02 02-22 02-21 02-20 02-25 02-24 03-01 03-01 02-28 02-26 02-25 02-24 02-23 02-21 02-27 02-23 02-08')),
 dict(k='emmys', rx=r'emmy', q='block', net=lambda y: {1984: 'cbs', 1985: 'abc', 1986: 'nbc', 1987: 'fox', 1993: 'abc', 1995: 'fox', 1996: 'abc', 1997: 'cbs', 1998: 'nbc', 1999: 'fox', 2000: 'abc', 2001: 'cbs', 2002: 'nbc', 2003: 'fox', 2004: 'abc'}.get(y, ''), o=1948, md=50, names=['Emmy Awards', 'Primetime Emmys'], d=yz(1984, '09-23 09-22 09-21 09-20 08-28 09-17 09-16 08-25 08-30 09-19 09-11 09-10 09-08 09-14 09-13 09-12 09-10 11-04 09-22 09-21 09-19')),
 dict(k='vmas', rx=r'video music awards|\bvmas?\b', q='block', net=lambda y: 'mtv', o=0, md=40, names=['MTV Video Music Awards', 'VMAs'], d=yz(1984, '09-14 09-13 09-05 09-11 09-07 09-06 09-06 09-05 09-09 09-02 09-08 09-07 09-04 09-04 09-10 09-09 09-07 09-06 08-29 08-28 08-29')),
 dict(k='amas', rx=r'american music awards', q='block', net=lambda y: 'abc', o=1973, md=50, names=['American Music Awards'], d=yz(1984, '01-16 01-28 01-27 01-26 01-25 01-30 01-22 01-28 01-27 01-25 02-07 01-30 01-29 01-27 01-26 01-11 01-17 01-08 01-09 01-13 11-14')),
 dict(k='globes', rx=r'golden globe', q='block', net=lambda y: 'nbc' if y >= 1996 else '', o=1943, md=50, names=['Golden Globe Awards', 'Golden Globes'], d=yz(1984, '01-28 01-27 01-24 01-31 01-23 01-28 01-20 01-19 01-18 01-24 01-22 01-21 01-21 01-19 01-18 01-24 01-23 01-21 01-20 01-19 01-25')),
 dict(k='election', rx=r'election (night|coverage|results|returns)|decision \d\d|vote \d\d|campaign \d\d', q='block', net=lambda y: '', o=0, md=40, names=['election night coverage', 'election night'], d={1984: '11-06', 1986: '11-04', 1988: '11-08', 1990: '11-06', 1992: '11-03', 1994: '11-08', 1996: '11-05', 1998: '11-03', 2000: '11-07', 2002: '11-05', 2004: '11-02'}),
 dict(k='nye', rx=r"new year'?s rockin|times square|new year'?s eve", q='block', net=lambda y: 'abc', o=0, md=30, names=["Dick Clark's New Year's Rockin' Eve", "New Year's Eve Times Square"], d={y: '12-31' for y in range(1984, 2005)}),
 dict(k='superbowl', rx=r'super bowl', q='sports', net=lambda y: {1984: 'cbs', 1985: 'abc', 1986: 'nbc', 1987: 'cbs', 1988: 'abc', 1989: 'nbc', 1990: 'cbs', 1991: 'abc', 1992: 'cbs', 1993: 'nbc', 1994: 'nbc', 1995: 'abc', 1996: 'nbc', 1997: 'fox', 1998: 'nbc', 1999: 'fox', 2000: 'abc', 2001: 'cbs', 2002: 'fox', 2003: 'abc', 2004: 'cbs'}[y], o=1966, md=90, names=['Super Bowl'], d=yz(1984, '01-22 01-20 01-26 01-25 01-31 01-22 01-28 01-27 01-26 01-31 01-30 01-29 01-28 01-26 01-25 01-31 01-30 01-28 02-03 01-26 02-01')),
]
ROM = ['', 'I', 'II', 'III', 'IV', 'V', 'VI', 'VII', 'VIII', 'IX', 'X', 'XI', 'XII', 'XIII', 'XIV', 'XV', 'XVI', 'XVII', 'XVIII', 'XIX', 'XX', 'XXI', 'XXII', 'XXIII', 'XXIV', 'XXV', 'XXVI', 'XXVII', 'XXVIII', 'XXIX', 'XXX', 'XXXI', 'XXXII', 'XXXIII', 'XXXIV', 'XXXV', 'XXXVI', 'XXXVII', 'XXXVIII']
BAD = re.compile(r'(?i)reaction|reacts|review|highlights?\b|podcast|excerpt|recap|top \d+|best moments|red carpet|trailer|parody|predictions|fan ?made|\bpart \d+ of\b|music only|audio only|game ?play|madden|simulation|nes |snes|sega|tecmo|2k\d|20(0[5-9]|1\d|2\d)')
have = json.load(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'eventfill_have.json'))) if os.path.exists(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'eventfill_have.json')) else {}
out = json.load(gzip.open(OUT, 'rt')) if os.path.exists(OUT) else []
seen = set(x['vid'] for x in out)
for E in (EV if not os.environ.get('ONLYTG') else []):
    for y, md in sorted(E['d'].items()):
        if y in set(have.get(E['k'], [])): continue
        if Y.left() < 300: break
        n = y - E['o'] if E['o'] else 0
        qs = [f"{y} {E['names'][0]} full broadcast", f"{E['names'][-1]} {y}"]
        if E['k'] == 'superbowl': qs = [f"Super Bowl {ROM[n]} full game {y}", f"Super Bowl {ROM[n]} {y} broadcast"]
        elif n: qs.append(f"{ordn(n)} {E['names'][0]}")
        best = []
        for q in qs:
            try: res = Y.search(q, pages=1)
            except Exception: res = []
            for c in res:
                t = c.get('t') or ''; low = t.lower(); dur = c.get('dur') or 0
                if c['vid'] in seen or c.get('live') or dur < E['md'] * 60 or BAD.search(t): continue
                if not re.search(E['rx'], low): continue
                yo = str(y) in t or (n and (ordn(n).lower() in low or (E['k'] == 'superbowl' and re.search(r'\b' + ROM[n].lower() + r'\b', low))))
                if not yo: continue
                if re.search(r'(?<!\d)(19[89]\d|200[0-4])(?!\d)', t) and str(y) not in t and E['k'] != 'superbowl': continue
                best.append(c)
            time.sleep(0.5 + random.random())
        best.sort(key=lambda c: (-(c.get('dur') or 0)))
        for c in best[:2 if E['k'] != 'superbowl' else 1]:
            seen.add(c['vid'])
            out.append({'i': 'yt:' + c['vid'], 'vid': c['vid'], 't': c['t'], 'ch': c.get('ch', ''), 'off': 0, 'dur': c['dur'], 'views': c.get('views', 0), 'q': E['q'], 'k': c['t'].upper()[:60], 'ad': f'{y}-{md}', 'as': 'fill', 'e': y, 'net': E['net'](y), 'ct': E['k'], 'why': 'eventfill'})
            print(E['k'], y, round(c['dur'] / 60), c['t'][:80], flush=True)
TG = """1984|Green Bay Packers|Detroit Lions|cbs;1984|New England Patriots|Dallas Cowboys|nbc;1985|New York Jets|Detroit Lions|nbc;1985|St. Louis Cardinals|Dallas Cowboys|cbs;1986|Green Bay Packers|Detroit Lions|cbs;1986|Seattle Seahawks|Dallas Cowboys|nbc;1987|Kansas City Chiefs|Detroit Lions|nbc;1987|Minnesota Vikings|Dallas Cowboys|cbs;1988|Minnesota Vikings|Detroit Lions|cbs;1988|Houston Oilers|Dallas Cowboys|nbc;1989|Cleveland Browns|Detroit Lions|nbc;1989|Philadelphia Eagles|Dallas Cowboys|cbs;1990|Denver Broncos|Detroit Lions|nbc;1990|Washington Redskins|Dallas Cowboys|cbs;1991|Chicago Bears|Detroit Lions|cbs;1991|Pittsburgh Steelers|Dallas Cowboys|nbc;1992|Houston Oilers|Detroit Lions|nbc;1992|New York Giants|Dallas Cowboys|cbs;1993|Chicago Bears|Detroit Lions|cbs;1993|Miami Dolphins|Dallas Cowboys|nbc;1994|Buffalo Bills|Detroit Lions|nbc;1994|Green Bay Packers|Dallas Cowboys|fox;1995|Minnesota Vikings|Detroit Lions|fox;1995|Kansas City Chiefs|Dallas Cowboys|nbc;1996|Kansas City Chiefs|Detroit Lions|nbc;1996|Washington Redskins|Dallas Cowboys|fox;1997|Chicago Bears|Detroit Lions|fox;1997|Tennessee Oilers|Dallas Cowboys|nbc;1998|Pittsburgh Steelers|Detroit Lions|cbs;1998|Minnesota Vikings|Dallas Cowboys|fox;1999|Chicago Bears|Detroit Lions|fox;1999|Miami Dolphins|Dallas Cowboys|cbs;2000|New England Patriots|Detroit Lions|cbs;2000|Minnesota Vikings|Dallas Cowboys|fox;2001|Green Bay Packers|Detroit Lions|fox;2001|Denver Broncos|Dallas Cowboys|cbs;2002|New England Patriots|Detroit Lions|cbs;2002|Washington Redskins|Dallas Cowboys|fox;2003|Green Bay Packers|Detroit Lions|fox;2003|Miami Dolphins|Dallas Cowboys|cbs;2004|Indianapolis Colts|Detroit Lions|cbs;2004|Chicago Bears|Dallas Cowboys|fox"""
import datetime
for row in TG.split(';'):
    if Y.left() < 300: break
    y, vis, home, net = row.split('|'); y = int(y)
    if 'tg:' + row in set(have.get('tgfb', [])): continue
    _vn, _hn = vis.split()[-1], home.split()[-1]
    if any(x.get('why') == 'tgfb' and x.get('k') == ('NFL THANKSGIVING: ' + _vn + ' AT ' + _hn).upper() and str(x.get('ad', '')).startswith(str(y)) and (x.get('parts') or not re.search(r'(?i)part [2-9]', x.get('t', ''))) for x in out): continue
    f = datetime.date(y, 11, 1).weekday(); th = 1 + ((3 - f) % 7) + 21
    vn, hn = vis.split()[-1], home.split()[-1]
    qs = [f"{y} Thanksgiving {vn} vs {hn}", f"{vn} at {hn} {y} Thanksgiving", f"{vis} vs {home} {y} full game", f"{y} {vn} {hn} thanksgiving part 1", f"{hn} vs {vn} {y} NFL", f"{y} {vn} at {hn} week 13"]
    best = []; parts = []
    for q in qs:
        try: res = Y.search(q, pages=1)
        except Exception: res = []
        for c in res:
            t = c.get('t') or ''; low = t.lower(); dur = c.get('dur') or 0
            if c['vid'] in seen or c.get('live') or BAD.search(t): continue
            if vn.lower() not in low or hn.lower() not in low: continue
            pm = re.search(r'(?i)\b(?:part|pt\.?)\s*(\d)', t)
            if pm and dur >= 600 and (str(y) in t or str(y)[2:] in t):
                parts.append((c.get('ch', ''), int(pm.group(1)), c)); continue
            if dur < 3600: continue
            if str(y) not in t and not ('thanksgiving' in low and str(y)[2:] in t): continue
            if re.search(r'(?<!\d)(19[89]\d|200[0-4])(?!\d)', t) and str(y) not in t: continue
            best.append(c)
        time.sleep(0.5 + random.random())
    best.sort(key=lambda c: -(c.get('dur') or 0))
    if not best or (best[0].get('dur') or 0) < 7200:
        byc = {}
        for ch, n, cc in parts: byc.setdefault(ch, {}).setdefault(n, cc)
        grp = max(byc.values(), key=lambda g: sum((v.get('dur') or 0) for v in g.values()), default={})
        if grp and 1 in grp and sum((v.get('dur') or 0) for v in grp.values()) >= 7200:
            pl = [grp[k] for k in sorted(grp)]
            for v in pl: seen.add(v['vid'])
            out.append({'i': 'yt:' + pl[0]['vid'], 'vid': pl[0]['vid'], 't': pl[0]['t'], 'ch': pl[0].get('ch', ''), 'off': 0, 'dur': sum(v['dur'] for v in pl), 'parts': [[v['vid'], v['dur']] for v in pl], 'views': pl[0].get('views', 0), 'q': 'sports', 'k': ('NFL THANKSGIVING: ' + vn + ' AT ' + hn).upper(), 'ad': '%d-11-%02d' % (y, th), 'net': net, 'why': 'tgfb', 'ct': ('NFL Thanksgiving: ' + vn + ' at ' + hn)})
            print('tgfb parts', y, vn, hn, len(pl), flush=True)
            continue
    for c in best[:1]:
        seen.add(c['vid'])
        out.append({'i': 'yt:' + c['vid'], 'vid': c['vid'], 't': c['t'], 'ch': c.get('ch', ''), 'off': 0, 'dur': c['dur'], 'views': c.get('views', 0), 'q': 'sports', 'k': ('NFL THANKSGIVING: ' + vn + ' AT ' + hn).upper(), 'ad': '%d-11-%02d' % (y, th), 'net': net, 'why': 'tgfb', 'ct': ('NFL Thanksgiving: ' + vn + ' at ' + hn)})
        print('tgfb', y, vn, hn, round(c['dur'] / 60), c['t'][:80], flush=True)
json.dump(out, gzip.open(OUT, 'wt'), ensure_ascii=False)
print('total', len(out))
