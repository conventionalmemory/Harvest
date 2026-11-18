import json, os, re, time, urllib.parse, urllib.request
here = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(here, 'thin_ids.txt')
UA = {'User-Agent': 'Mozilla/5.0 (retrotv-sources harvester)'}
def get(url, tries=4):
    for k in range(tries):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=90) as r:
                return json.loads(r.read().decode('utf-8', 'replace'))
        except Exception as e:
            if k == tries - 1: print('fail', url[:120], e, flush=True); return None
            time.sleep(4 * (k + 1))
def search(q, cap):
    out, cur = [], None
    while len(out) < cap:
        u = 'https://archive.org/services/search/v1/scrape?' + urllib.parse.urlencode({'q': q, 'fields': 'identifier,title,year,subject,date', 'count': 1000}) + ('&cursor=' + urllib.parse.quote(cur) if cur else '')
        j = get(u)
        if not j: break
        out += j.get('items', [])
        cur = j.get('cursor')
        if not cur: break
    return out[:cap]
def txt(x):
    v = []
    for k in ('title', 'subject'):
        s = x.get(k) or ''
        v.append(' '.join(s) if isinstance(s, list) else str(s))
    return ' '.join(v)
def yr(x):
    for k in ('year', 'date'):
        m = re.search(r'(19[0-9]\d|200[0-4])', str(x.get(k) or ''))
        if m: return m.group(1)
    m = re.search(r'(?<!\d)(19[2-9]\d|200[0-4])(?!\d)', txt(x) + ' ' + x['identifier'])
    return m.group(1) if m else '0'
have = set()
for f in ('extra_ids.txt', 'thin_ids.txt'):
    p = os.path.join(here, f)
    if os.path.exists(p): have |= {l.split()[1] for l in open(p) if len(l.split()) > 1}
rows = []
CD = re.compile(r'(?i)civil defen|atom|nuclear|\bbomb|fallout|radiolog|duck and cover|survival|disaster|air raid|shelter')
TR = re.compile(r'(?i)training|industrial|safety|how to|sales(man)?\b|instruction|occupation|\bjob\b|employee|military|army|navy|air force|marine corps|first aid|driver|driving|factory|worker')
AD = re.compile(r'(?i)advertis|commercial|\bad film|home movie|amateur film|outtake|trailer|stock footage|newsreel')
n = {'edu': 0, 'cd': 0, 'train': 0, 'jgame': 0}
for x in search('collection:prelinger AND mediatype:movies', 9000):
    i = x['identifier']; t = txt(x); y = yr(x)
    if i in have or AD.search(t) or not ('1930' <= y <= '1999'): continue
    q = 'cd' if CD.search(t) else 'train' if TR.search(t) else 'edu'
    rows.append((q, i, y)); have.add(i); n[q] += 1
JSHOW = re.compile(r"(?i)takeshi|tetsujin|iron ?chef|sasuke|banzuke|gaki ?no ?tsukai|downtown|tunnels|hey!? ?hey!? ?hey|naruhodo|tv champion|denpa|ucchan|waratte ?ii|mecha.?mecha|batsu|kasou ?taishou|most extreme elimination|\bmxc\b|quiz|game show|variety|hyokin|tokoro|dotch|nep league|vs ?arashi|food battle|unbelievable|show by shobai|クイズ|バラエティ|ゲーム|笑って|料理の鉄人|風雲たけし城")
JBAD = re.compile(r'(?i)anime|\bova\b|episode \d+ eng|dorama|drama|\bnews\b|baseball|soccer|sumo|keiba|commercials?\b|\bcm\b|\bcms\b|opening|ending|\bop\b|\bed\b|music video|concert|movie|film|trailer')
JQ = ['mediatype:movies AND (title:(JOAX OR JOCX OR JOKX OR JORX OR JOEX OR JOTX OR JODX OR JOBK OR JOAR OR JOOX) OR identifier:(*joax* OR *jocx* OR *jokx* OR *jorx* OR *joex* OR *jotx* OR *jodx*))',
      'mediatype:movies AND (takeshi OR tetsujin OR "iron chef" OR sasuke OR banzuke OR "gaki no tsukai" OR "most extreme elimination" OR "naruhodo the world" OR "tv champion" OR "denpa shonen" OR "ucchan nanchan" OR "kasou taishou" OR "japanese game show" OR "japanese variety" OR "batsu game")']
for qq in JQ:
    for x in search(qq, 4000):
        i = x['identifier']; t = txt(x) + ' ' + i.replace('-', ' ').replace('_', ' '); y = yr(x)
        if i in have or not JSHOW.search(t) or JBAD.search(t) or y > '2004': continue
        rows.append(('jgame', i, y if y != '0' else '0')); have.add(i); n['jgame'] += 1
with open(OUT, 'a') as f:
    for r in rows: f.write(' '.join(r) + '\n')
print('thin', n, len(rows))
