import gzip, json, os, re, sys, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import yt_events as E
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, 'catalog', 'yt_realism.json.gz')
BUDGET = float(os.environ.get('BUDGET_MIN', '50')) * 60; T0 = time.time()
GROUPS = [g for g in os.environ.get('GROUPS', 'promo,special,localnews,infomercial').split(',') if g]
BAD = re.compile(r"(?i)reaction|review|unboxing|tutorial|how to|then and now|minecraft|roblox|gmod|\bmod\b|blender|simulat|recreat|remake|parody|\bfake\b|\b20(0[5-9]|1\d|2\d)\b(?!\s*(remaster|upload|transfer))")
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
NETS = ['NBC', 'ABC', 'CBS', 'FOX', 'Nickelodeon', 'Nick at Nite', 'MTV', 'VH1', 'USA Network', 'TBS', 'WGN', 'Cartoon Network', 'Disney Channel', 'HBO', 'Showtime', 'Cinemax', 'A&E', 'ESPN', 'Comedy Central', 'TNT', 'Lifetime', 'PBS', 'CNN', 'Discovery Channel', 'TNN', 'BET', 'Sci-Fi Channel', 'UPN', 'The WB', 'Fox Kids']
Q = {'promo': [], 'special': [], 'localnews': [], 'infomercial': []}
for n in NETS:
    for y in range(1984, 2005):
        Q['promo'].append('%s promo %d' % (n, y))
    Q['promo'] += ['%s station id 1980s' % n, '%s station id 1990s' % n, '%s bumpers 1990s' % n]
Q['special'] = ['challenger explosion live coverage 1986', 'ABC news special report challenger', 'CBS news special report challenger', 'NBC news special report challenger 1986', 'CNN challenger live 1986', 'gulf war begins live coverage january 16 1991', 'ABC news special report gulf war 1991', 'CBS news special report gulf war 1991', 'NBC news special report persian gulf 1991', 'CNN baghdad bombing live 1991', 'OJ simpson bronco chase live coverage', 'OJ simpson verdict live 1995', 'princess diana death news coverage 1997', 'september 11 2001 live coverage ABC', 'september 11 2001 live coverage CBS', 'september 11 2001 live coverage NBC', 'september 11 2001 CNN live', 'oklahoma city bombing special report 1995', 'columbine shooting news special report 1999', 'rodney king verdict special report 1992', 'waco siege fire special report 1993', 'berlin wall falls news coverage 1989', 'san francisco earthquake world series 1989 live', 'loma prieta earthquake ABC coverage', 'reagan assassination attempt special report', 'iran contra special report 1987', 'space shuttle columbia disaster live 2003', 'iraq war begins live coverage 2003', 'saddam hussein captured special report 2003', 'clinton impeachment special report 1998', 'bush gore election night 2000', 'tiananmen square news coverage 1989', 'hurricane andrew special report 1992', 'northridge earthquake live coverage 1994', 'TWA flight 800 special report 1996', 'jfk jr plane crash special report 1999', 'mt st helens special report', 'news special report 1980s', 'news bulletin interrupts 1980s', 'news special report interruption 1990s', 'nbc news special report 1980s', 'cbs news special report 1980s', 'abc news special report 1980s', 'cnn breaking news 1990s']
for st in ['WREX', 'WIFR', 'WTVO', 'WQRF', 'Rockford']:
    Q['localnews'] += ['%s news %s' % (st, y) for y in ('1984', '1987', '1990', '1993', '1996', '1999', '2002', '1980s', '1990s')]
for st in ['WGN news', 'WLS eyewitness news', 'WMAQ news', 'WBBM news', 'WFLD news', 'Chicago news']:
    Q['localnews'] += ['%s %s' % (st, y) for y in ('1985', '1988', '1991', '1994', '1997', '2000', '2003', '1980s', '1990s')]
Q['infomercial'] = ['infomercial %d' % y for y in range(1985, 2005)] + ['%s infomercial' % p for p in ['Ronco', 'Ginsu knives', 'Psychic Friends Network', 'Bowflex', 'ThighMaster', 'Proactiv', 'George Foreman grill', 'Ab Roller', 'Flowbee', 'Soloflex', 'Showtime Rotisserie', 'Tae Bo', 'Popeil pasta maker', 'Miss Cleo', 'Hair Club for Men', 'Richard Simmons', 'Susan Powter', 'Tony Robbins', 'Don Lapre', 'Carlton Sheets', 'Nordictrack', 'Total Gym', 'Bun and Thigh Roller', 'Smokeless ashtray', 'Body by Jake', 'Hooked on Phonics', 'Time Life music', 'Ab Isolator', 'Deal-a-Meal', 'GLH spray hair', 'Thane Orbitrek', 'Juiceman', 'Jack LaLanne juicer', 'Oxiclean', 'Space Bag', 'Magic Jack', 'Girls Gone Wild']] + ['paid programming 1990s', 'full infomercial vhs 1990s', '30 minute infomercial 1990s', 'late night infomercial 1980s']
LEN = {'promo': (8, 240), 'special': (30, 14400), 'localnews': (60, 7200), 'infomercial': (600, 3700)}
KEEP = {'promo': re.compile(r'(?i)promo|bumper|\bids?\b|station id|ident|commercials? and promos|tonight on|this week on|coming up|image campaign|sign[- ]?on|sign[- ]?off'), 'special': re.compile(r'(?i)special report|bulletin|breaking|live coverage|coverage|news|cnn|abc|cbs|nbc'), 'localnews': re.compile(r'(?i)news|newscast|eyewitness|action news|report|anchor|weather'), 'infomercial': re.compile(r'(?i)infomercial|paid program|commercial|full|\bshow\b|offer|ronco|popeil|psychic|bowflex|thigh|proactiv|foreman|ab roller|flowbee|soloflex|tae bo|cleo|hair club|simmons|powter|robbins|lapre|sheets|nordic|total gym|phonics|time life|deal-a-meal|glh|juice|oxiclean|space bag|ab isolator|orbitrek')}
seen = {}
for g in GROUPS:
    for n, q in enumerate(Q[g]):
        if time.time() - T0 > BUDGET: break
        try: rs = E.search(q, pages=1 if g == 'promo' else 2, long=False)
        except Exception as e: print('fail', q, e, flush=True); continue
        lo, hi = LEN[g]
        for r in rs:
            t = r.get('t') or ''; d = int(r.get('dur') or 0)
            if BAD.search(t) or not KEEP[g].search(t) or not (lo <= d <= hi): continue
            ad = date_of(t)
            if not ad and g != 'infomercial': continue
            k = r['vid']
            if k not in seen: seen[k] = {'vid': k, 't': t[:200], 'ch': (r.get('ch') or '')[:80], 'dur': d, 'ad': ad, 'g': g, 'q': q}
        if n % 25 == 0: print(g, n, len(Q[g]), q, 'kept', len(seen), round((time.time() - T0) / 60, 1), flush=True)
L = sorted(seen.values(), key=lambda x: (x['g'], x['ad'], x['vid']))
os.makedirs(os.path.dirname(OUT), exist_ok=True)
json.dump(L, gzip.open(OUT, 'wt', encoding='utf-8'), ensure_ascii=False, separators=(',', ':'))
c = {}
for x in L: c[x['g']] = c.get(x['g'], 0) + 1
print('kept', len(L), c, dict(E.STATS), flush=True)
