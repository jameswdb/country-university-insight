# -*- coding: utf-8 -*-
"""Semantic Scholar enrichment (keyed): influential citations, TLDRs, S2 metrics.

What it adds on top of OpenAlex
  * influentialCitationCount - citations that actually mattered (per paper, summed per person)
  * tldr                     - one-line summary of the person's most influential paper
  * an independent paper/citation count and h-index from a different pipeline
  * affiliations / homepage from the S2 author profile

Two request shapes per person
  GET /author/search?query=<name>&fields=<author fields>  -> pick by ORCID when possible
  GET /author/<id>/papers?fields=...&limit=100            -> influential sum + top papers

The papers request is the expensive half, so it is only issued for the top N people
per university (TOP env, default 60). Everyone else gets metrics only.

Resumable: one JSONL per university under data/raw/s2/.
Set S2_API_KEY. Paced at 0.55 s, backs off on 429.

Usage
  S2_API_KEY=... python 11_semantic_scholar.py           # top 60/uni with papers
  S2_API_KEY=... TOP=0 python 11_semantic_scholar.py     # full A-tier, metrics only
  S2_API_KEY=... python 11_semantic_scholar.py --probe
"""
import urllib.request, urllib.error, urllib.parse, ssl, json, io, os, sys, time, threading
from concurrent.futures import ThreadPoolExecutor, as_completed

if __name__ == '__main__':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONF = json.load(open(os.path.join(ROOT, 'config', 'universities.json'), encoding='utf-8'))
PROC = os.path.join(ROOT, 'data', 'processed')
RAW = os.path.join(ROOT, 'data', 'raw', 's2')
os.makedirs(RAW, exist_ok=True)

KEY = os.environ.get('S2_API_KEY', '').strip()
TOP = int(os.environ.get('TOP', '60'))
MIN_WORKS = int(os.environ.get('MIN_WORKS', '15'))
PACE = float(os.environ.get('PACE', '0.55'))
LIMIT = int(os.environ.get('LIMIT', '0'))     # cap people per university (0 = all)
WORKERS = int(os.environ.get('WORKERS', '3'))
MIN_INTERVAL = float(os.environ.get('MIN_INTERVAL', '0.30'))
_gate = threading.Lock()
_last = [0.0]


def _throttle():
    """Global pacing: keep request starts at least MIN_INTERVAL apart across threads."""
    with _gate:
        now = time.time()
        wait = _last[0] + MIN_INTERVAL - now
        if wait > 0:
            time.sleep(wait)
            now = time.time()
        _last[0] = now
BASE = 'https://api.semanticscholar.org/graph/v1'
CTX = ssl.create_default_context()
CTX.check_hostname = False
CTX.verify_mode = ssl.CERT_NONE
UA = {'User-Agent': 'IsraelInsight/1.0 (academic research)'}
AUTHOR_FIELDS = 'name,affiliations,homepage,paperCount,citationCount,hIndex,externalIds'
PAPER_FIELDS = 'title,year,venue,citationCount,influentialCitationCount'


def api(path, params=None, tries=5):
    _throttle()
    q = urllib.parse.urlencode(params or {})
    url = f'{BASE}{path}' + (f'?{q}' if q else '')
    headers = dict(UA)
    if KEY:
        headers['x-api-key'] = KEY
    for i in range(tries):
        try:
            r = urllib.request.urlopen(urllib.request.Request(url, headers=headers),
                                       timeout=40, context=CTX)
            return json.loads(r.read().decode('utf-8'))
        except urllib.error.HTTPError as e:
            if e.code == 429:
                ra = e.headers.get('Retry-After') if e.headers else None
                try:
                    wait = max(1.0, float(ra))
                except (TypeError, ValueError):
                    wait = min(30.0, 2.0 * (i + 1))
                time.sleep(wait)
                continue
            if e.code == 404:
                return None
            if e.code == 400:
                return {'__bad__': e.read()[:120].decode('utf-8', 'replace')}
            time.sleep(1.5 * (i + 1))
        except Exception:
            time.sleep(1.5 * (i + 1))
    return None


def match(name, orcid=None):
    d = api('/author/search', {'query': name, 'fields': AUTHOR_FIELDS, 'limit': 5})
    if not d or d.get('__bad__') or not d.get('data'):
        return None
    if orcid:
        for a in d['data']:
            ext = a.get('externalIds') or {}
            if (ext.get('ORCID') or '').replace('-', '') == orcid.replace('-', ''):
                return a
    return d['data'][0]


def papers(author_id, limit=100):
    d = api(f'/author/{author_id}/papers', {'fields': PAPER_FIELDS, 'limit': limit})
    if not d or d.get('__bad__'):
        return []
    return [p for p in d.get('data', []) if p.get('title')]


def paper_tldr(paper_id):
    if not paper_id:
        return None
    d = api(f'/paper/{paper_id}', {'fields': 'title,tldr'})
    if not d or d.get('__bad__'):
        return None
    return (d.get('tldr') or {}).get('text')


def probe():
    d = api('/author/search', {'query': 'Yeala Shaked',
                               'fields': 'name,paperCount,citationCount,hIndex', 'limit': 1})
    if d and not d.get('__bad__') and d.get('data'):
        print('probe OK:', json.dumps(d['data'][0], ensure_ascii=False))
        return True
    print('probe FAILED:', d)
    return False


def main():
    if '--probe' in sys.argv:
        probe()
        return
    if not KEY:
        raise SystemExit('S2_API_KEY is required for the keyed path')
    grand = 0
    for uni in CONF['universities']:
        code = uni['code']
        fp = os.path.join(PROC, code, 'faculty.json')
        if not os.path.exists(fp):
            continue
        rows = json.load(open(fp, encoding='utf-8'))
        pool = [r for r in rows
                if r.get('tier') == 'A' and r.get('name')
                and (r.get('works_10y') or 0) >= MIN_WORKS]
        pool.sort(key=lambda r: -(r.get('works_total') or 0))
        if LIMIT:
            pool = pool[:LIMIT]
        outp = os.path.join(RAW, f'{code}.jsonl')
        done = set()
        if os.path.exists(outp):
            for line in open(outp, encoding='utf-8'):
                try:
                    done.add(json.loads(line)['key'])
                except Exception:
                    pass
        todo = [r for r in pool if (r.get('id') or r['name']) not in done]
        print(f'[{code}] pool={len(pool)} done={len(done)} todo={len(todo)} '
              f'(papers for first {TOP})', flush=True)
        def work(item):
            idx, r = item
            key = r.get('id') or r['name']
            a = match(r['name'], r.get('orcid'))
            if not a:
                return {'key': key, 'name': r['name'], 's2': None}
            rec = {'key': key, 'name': r['name'], 's2': {
                'authorId': a['authorId'], 'name': a.get('name'),
                'affiliations': a.get('affiliations'), 'homepage': a.get('homepage'),
                'paperCount': a.get('paperCount'), 'citationCount': a.get('citationCount'),
                'hIndex': a.get('hIndex'), 'externalIds': a.get('externalIds')}}
            if idx < TOP:
                ps = papers(a['authorId'])
                infl = sum((p.get('influentialCitationCount') or 0) for p in ps)
                ps_sorted = sorted(ps, key=lambda p: -(p.get('influentialCitationCount')
                                                       or p.get('citationCount') or 0))
                rec['influential_sum'] = infl
                rec['papers_sampled'] = len(ps)
                rec['top_papers'] = [{
                    'paperId': p.get('paperId'),
                    'title': p.get('title'), 'year': p.get('year'), 'venue': p.get('venue'),
                    'citations': p.get('citationCount'),
                    'influential': p.get('influentialCitationCount'),
                } for p in ps_sorted[:3]]
                # TLDR lives on the paper object, not on the author-papers list
                if rec['top_papers']:
                    rec['top_papers'][0]['tldr'] = paper_tldr(rec['top_papers'][0]['paperId'])
            return rec

        with open(outp, 'a', encoding='utf-8') as fh:
            with ThreadPoolExecutor(max_workers=WORKERS) as ex:
                futs = {ex.submit(work, (i, r)): i for i, r in enumerate(todo)}
                finished = 0
                for fut in as_completed(futs):
                    try:
                        rec = fut.result()
                    except Exception:
                        continue
                    fh.write(json.dumps(rec, ensure_ascii=False) + '\n')
                    fh.flush()
                    finished += 1
                    if rec.get('s2'):
                        grand += 1
                    if finished % 20 == 0:
                        print(f'[{code}] {finished}/{len(todo)} matched={grand}', flush=True)
        print(f'[{code}] done', flush=True)
    print(f'[s2] fetched {grand}', flush=True)


if __name__ == '__main__':
    main()
