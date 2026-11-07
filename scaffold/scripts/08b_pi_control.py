# -*- coding: utf-8 -*-
"""Control sample for the PI validation: top C-tier researchers per university.

C-tier is mostly doctoral students and postdocs. If the tier rule captures
principal investigators, their last-author share must be clearly lower than the
A-tier sample. Sampling 20 per university keeps the cost negligible.

Appends to the same pi.jsonl with a "tier" field.
Output: insight/data/processed/<CODE>/pi.jsonl (supplementary rows)
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
N = int(os.environ.get('CTRL', '20'))
WORKERS = 6


def api(url, tries=3):
    sep = '&' if '?' in url else '?'
    for i in range(tries):
        try:
            return json.load(urllib.request.urlopen(
                urllib.request.Request(f'{url}{sep}api_key={KEY}', headers=UA),
                timeout=90, context=CTX))
        except urllib.error.HTTPError as e:
            if e.code in (403, 429):
                return {'__quota__': True}
            time.sleep(1.0 * (i + 1))
        except Exception:
            time.sleep(1.0 * (i + 1))
    return None


def signal(aid):
    d = api(f'https://api.openalex.org/works?filter=author.id:{aid}'
            '&sort=cited_by_count:desc&per_page=100&select=id,publication_year,authorships,type')
    if d is None or d.get('__quota__'):
        return None
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
    for uni in CONF['universities']:
        code = uni['code']
        fac = json.load(open(os.path.join(PROC, code, 'faculty.json'), encoding='utf-8'))
        out = os.path.join(PROC, code, 'pi.jsonl')
        done = set()
        if os.path.exists(out):
            for line in open(out, encoding='utf-8'):
                try:
                    done.add(json.loads(line)['id'])
                except Exception:
                    pass
        ctrl = [r for r in fac if r.get('tier') == 'C' and r.get('id')]
        ctrl.sort(key=lambda r: -(r.get('works_total') or 0))
        todo = [r for r in ctrl if r['id'] not in done][:N]
        if not todo:
            print(f'[{code}] control done', flush=True)
            continue
        with open(out, 'a', encoding='utf-8') as fh:
            with ThreadPoolExecutor(max_workers=WORKERS) as ex:
                futs = {ex.submit(signal, r['id']): r for r in todo}
                for fut in as_completed(futs):
                    r = futs[fut]
                    sig = fut.result()
                    if not sig:
                        continue
                    fh.write(json.dumps({'id': r['id'], 'name': r.get('name'),
                                         'tier': 'C', **sig}, ensure_ascii=False) + '\n')
        print(f'[{code}] control {len(todo)}', flush=True)


if __name__ == '__main__':
    main()
