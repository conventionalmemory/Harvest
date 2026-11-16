import gzip, json, os, re, sys, urllib.parse, urllib.request
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
UA = 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36'
def get(u):
    try:
        with urllib.request.urlopen(urllib.request.Request(u, headers={'User-Agent': UA}), timeout=60) as r:
            return r.status, r.read()
    except Exception as e:
        return 0, str(e).encode()
out = {}
for base in [x for x in os.environ.get('URLS', '').split() if x]:
    st, b = get(base)
    html = b.decode('utf-8', 'replace')
    out[base] = {'st': st, 'body': html}
    refs = set(re.findall(r'''(?:src|href)=["']([^"']+\.(?:js|mjs|json)(?:\?[^"']*)?)["']''', html))
    refs |= set(re.findall(r'''import\s*\(?\s*["']([^"']+\.m?js)["']''', html))
    for ref in sorted(refs):
        u = urllib.parse.urljoin(base, ref)
        if urllib.parse.urlparse(u).netloc != urllib.parse.urlparse(base).netloc: continue
        st2, b2 = get(u)
        t = b2.decode('utf-8', 'replace')
        out[u] = {'st': st2, 'body': t if len(t) < 3000000 else t[:3000000]}
        for ref2 in set(re.findall(r'''["']([./\w-]+\.m?js)["']''', t)):
            u2 = urllib.parse.urljoin(u, ref2)
            if u2 in out or urllib.parse.urlparse(u2).netloc != urllib.parse.urlparse(base).netloc: continue
            st3, b3 = get(u2)
            out[u2] = {'st': st3, 'body': b3.decode('utf-8', 'replace')[:3000000]}
    st4, b4 = get(urllib.parse.urljoin(base, 'd.json'))
    out[urllib.parse.urljoin(base, 'd.json')] = {'st': st4, 'body': b4.decode('utf-8', 'replace')[:20000]}
os.makedirs(os.path.join(ROOT, 'parts'), exist_ok=True)
json.dump(out, gzip.open(os.path.join(ROOT, 'parts', 'sitesrc.json.gz'), 'wt', encoding='utf-8'))
print({k: (v['st'], len(v['body'])) for k, v in out.items()})
