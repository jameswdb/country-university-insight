# -*- coding: utf-8 -*-
"""Principal-investigator signal: last-author share on each author's top-cited works.

In Israeli STEM the PI is conventionally last author and students are first author,
so this ratio is a cheap, robust PI indicator that does not need full publication
lists. Sampling is concurrent (6 workers) because each work query is heavy.

Sample: top N A-tier researchers per university by lifetime output (default 100).

Output: insight/data/processed/<CODE>/pi.jsonl
"""
import urllib.request, urllib.error, ssl, json, io, os, sys, time
from concurrent.futures import ThreadPoolExecutor, as_completed

if __name__ == '__main__':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONF = json.load(open(os.path.join(ROOT, 'config', 'universities.json'), encoding='utf-8'))
PROC = os.path.join(ROOT, 'data', 'processed')
KEY = os.environ.get('OPENALEX_API_KEY', 'fidb8YhfPZOjbN6aeasj1g')
CTX = ssl.create_default_context()
CTX.check_hostname = False
CTX.verify_mode = ssl.CERT_NONE
UA = {'User-Agent': 'israel-insight/1.0 (academic research)'}
OK_TYPES = {'article', 'review', 'preprint', 'conference-paper', 'book-chapter'}
SAMPLE = int(os.environ.get('SAMPLE', '100'))
WORKERS = int(os.environ.get('WORKERS', '6'))


def api(url, tries=3):
    sep = '&' if '?' in url else '?'
    for i in range(tries):
        try:
            return json.load(urllib.request.urlopen(
                urllib.request.Request(f'{url}{sep}api_key={KEY}', headers=UA),
                timeout=90, context=CTX))
        except urllib.error.HTTPError as e:
            body = e.read()[:200].decode('utf-8', 'replace')
            if e.code in (403, 429):
                return {'__quota__': True, 'body': body}
            time.sleep(1.0 * (i + 1))
        except Exception:
            time.sleep(1.0 * (i + 1))
    return None


def signal(aid):
    d = api(f'https://api.openalex.org/works?filter=author.id:{aid}'
            '&sort=cited_by_count:desc&per_page=100&select=id,publication_year,authorships,type')
    if d is None:
        return None
    if d.get('__quota__'):
        return {'__quota__': True}
    first = last = n = 0
    for w in d.get('results', []):
        if (w.get('type') or '') not in OK_TYPES:
            continue
        au = w.get('authorships') or []
        pos = [k for k, x in enumerate(au) if ((x.get('author') or {}).get('id') or '').endswith(aid)]
        if not pos:
            continue
        n += 1
        if pos[0] == 0:
            first += 1
        if pos[0] == len(au) - 1 and len(au) > 1:
            last += 1
    return {'sampled': n, 'first': first, 'last': last,
            'last_share': round(last / n, 3) if n else 0.0}


def main():
    only = os.environ.get('UNIS', '').strip()
    for uni in CONF['universities']:
        code = uni['code']
        if only and code not in only.split(','):
            continue
        fac = json.load(open(os.path.join(PROC, code, 'faculty.json'), encoding='utf-8'))
        out = os.path.join(PROC, code, 'pi.jsonl')
        done = set()
        if os.path.exists(out):
            for line in open(out, encoding='utf-8'):
                try:
                    done.add(json.loads(line)['id'])
                except Exception:
                    pass
        pool = [r for r in fac if r.get('tier') == 'A' and r.get('id')]
        pool.sort(key=lambda r: -(r.get('works_total') or 0))
        need = max(0, SAMPLE - len(done))
        todo = [r for r in pool if r['id'] not in done][:need]
        print(f'[{code}] A-tier={len(pool)} done={len(done)} todo={len(todo)}', flush=True)
        if not todo:
            continue
        t0 = time.time()
        quota = False
        with open(out, 'a', encoding='utf-8') as fh:
            with ThreadPoolExecutor(max_workers=WORKERS) as ex:
                futs = {ex.submit(signal, r['id']): r for r in todo}
                for i, fut in enumerate(as_completed(futs)):
                    r = futs[fut]
                    sig = fut.result()
                    if sig is None:
                        continue
                    if sig.get('__quota__'):
                        quota = True
                        break
                    fh.write(json.dumps({'id': r['id'], 'name': r.get('name'), **sig},
                                        ensure_ascii=False) + '\n')
                    if i % 50 == 0:
                        fh.flush()
                        print(f'[{code}] {i}/{len(todo)} t={time.time()-t0:.0f}s', flush=True)
        print(f'[{code}] pi done {len(todo)} in {time.time()-t0:.0f}s', flush=True)
        if quota:
            print('[pi] quota hit; rerun to resume', flush=True)
            return


if __name__ == '__main__':
    main()
