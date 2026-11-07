# -*- coding: utf-8 -*-
"""Download OpenAlex author profiles for every university in config/universities.json.

Cheap by design: one paged author query per partition, no per-author calls. The
profile already carries `counts_by_year`, `topics` and `last_known_institutions`,
which is everything the analysis needs.

Output: insight/data/raw/<CODE>/p00001.json ...
        insight/data/raw/<CODE>/state.json
"""
import urllib.request, urllib.error, urllib.parse, ssl, json, io, os, sys, time

if __name__ == '__main__':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONF = json.load(open(os.path.join(ROOT, 'config', 'universities.json'), encoding='utf-8'))
KEY = os.environ.get('OPENALEX_API_KEY', 'fidb8YhfPZOjbN6aeasj1g')
SELECT = ','.join(['id', 'orcid', 'display_name', 'works_count', 'cited_by_count',
                   'summary_stats', 'topics', 'last_known_institutions', 'affiliations',
                   'counts_by_year'])
PER_PAGE = 200
PARTS = [('A', '2-5'), ('B', '6-10'), ('C', '11-20'), ('D', '21-40'),
         ('E', '41-80'), ('F', '81-160'), ('G', '161-320'), ('H', '321-100000')]

CTX = ssl.create_default_context()
CTX.check_hostname = False
CTX.verify_mode = ssl.CERT_NONE
UA = {'User-Agent': 'israel-insight/1.0 (academic research)'}


def fetch(url, tries=4):
    last = None
    for i in range(tries):
        try:
            return json.load(urllib.request.urlopen(urllib.request.Request(url, headers=UA),
                                                    timeout=90, context=CTX))
        except urllib.error.HTTPError as e:
            body = e.read()[:200].decode('utf-8', 'replace')
            if e.code in (403, 429):
                return {'__quota__': True, 'body': body}
            last = f'HTTP{e.code} {body}'
        except Exception as e:
            last = f'{type(e).__name__}: {e}'
        time.sleep(1.5 * (i + 1))
    raise RuntimeError(last)


def one(uni, only=''):
    code, oid = uni['code'], uni['openalex_id']
    base = os.path.join(ROOT, 'data', 'raw', code)
    os.makedirs(base, exist_ok=True)
    spath = os.path.join(base, 'state.json')
    state = json.load(open(spath, encoding='utf-8')) if os.path.exists(spath) else {}
    for pid, wc in PARTS:
        if only and pid not in only.split(','):
            continue
        st = state.setdefault(pid, {'wc': wc, 'pages': 0, 'records': 0, 'total': None, 'done': False})
        if st['done']:
            continue
        page = st['pages'] + 1
        while True:
            flt = f'last_known_institutions.id:{oid},works_count:{wc}'
            url = (f'https://api.openalex.org/authors?filter={flt}&sort=id:asc'
                   f'&per_page={PER_PAGE}&page={page}&select={SELECT}&api_key={KEY}')
            d = fetch(url)
            if d.get('__quota__'):
                print(f'[{code}] QUOTA {pid} p{page}: {d.get("body","")[:120]}', flush=True)
                json.dump(state, open(spath, 'w', encoding='utf-8'), indent=2)
                return 'quota'
            res = d.get('results', [])
            if st['total'] is None:
                st['total'] = d['meta'].get('count')
            json.dump({'count': st['total'], 'results': res},
                      open(os.path.join(base, f'{pid}_{page:05d}.json'), 'w', encoding='utf-8'),
                      ensure_ascii=False)
            st['pages'] = page
            st['records'] += len(res)
            json.dump(state, open(spath, 'w', encoding='utf-8'), indent=2)
            if not res or page * PER_PAGE >= (st['total'] or 0):
                st['done'] = True
                json.dump(state, open(spath, 'w', encoding='utf-8'), indent=2)
                break
            page += 1
            time.sleep(0.12)
        print(f'[{code}] part {pid} {st["records"]}/{st["total"]}', flush=True)
    return 'ok'


def main():
    only_codes = os.environ.get('UNIS', '').strip()
    t0 = time.time()
    for uni in CONF['universities']:
        if uni.get('existing_data'):
            print(f'[{uni["code"]}] skipped (curated data exists)', flush=True)
            continue
        if only_codes and uni['code'] not in only_codes.split(','):
            continue
        r = one(uni)
        if r == 'quota':
            print('[dl] stopped on quota; rerun to resume', flush=True)
            return
    print(f'[dl] done in {time.time()-t0:.0f}s', flush=True)


if __name__ == '__main__':
    main()
