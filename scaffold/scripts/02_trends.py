# -*- coding: utf-8 -*-
"""Institution-level trend aggregates for every university (2016-2026).

Nine `group_by` queries per university: output per year, topic mix, two topic
windows, country collaboration, types, open access. TAU and Technion reuse the
aggregates already produced by their earlier projects.

Output: insight/data/processed/<CODE>/institution_trends.json
"""
import urllib.request, urllib.error, urllib.parse, ssl, json, io, os, sys, time

if __name__ == '__main__':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONF = json.load(open(os.path.join(ROOT, 'config', 'universities.json'), encoding='utf-8'))
KEY = os.environ.get('OPENALEX_API_KEY', 'fidb8YhfPZOjbN6aeasj1g')
CTX = ssl.create_default_context()
CTX.check_hostname = False
CTX.verify_mode = ssl.CERT_NONE
UA = {'User-Agent': 'israel-insight/1.0 (academic research)'}
START, END = '2016-01-01', '2026-12-31'

STEPS = [
    ('years', 'publication_year', ''),
    ('topics', 'topics.id', ''),
    ('countries', 'authorships.countries', ''),
    ('types', 'type', ''),
    ('open_access', 'open_access.is_oa', ''),
    ('early_topics', 'topics.id', ',to_publication_date:2020-12-31'),
    ('late_topics', 'topics.id', ',from_publication_date:2021-01-01'),
]
EXISTING = {
    'TAU': 'D:/dev/University-IL/data/processed/institution_trends.json',
    'TECH': 'D:/dev/University-IL/technion/data/processed/institution_trends.json',
}


def get(url):
    try:
        return json.load(urllib.request.urlopen(urllib.request.Request(url, headers=UA),
                                                timeout=120, context=CTX))
    except urllib.error.HTTPError as e:
        if e.code in (403, 429):
            return {'__quota__': True, 'body': e.read()[:200].decode('utf-8', 'replace')}
        return None
    except Exception:
        return None


def main():
    only = os.environ.get('UNIS', '').strip()
    for uni in CONF['universities']:
        code, oid = uni['code'], uni['openalex_id']
        outdir = os.path.join(ROOT, 'data', 'processed', code)
        os.makedirs(outdir, exist_ok=True)
        out_path = os.path.join(outdir, 'institution_trends.json')
        if os.path.exists(out_path) and os.path.getsize(out_path) > 2000:
            print(f'[{code}] trends cached', flush=True)
            continue
        if code in EXISTING and os.path.exists(EXISTING[code]):
            src = json.load(open(EXISTING[code], encoding='utf-8'))
            json.dump(src, open(out_path, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
            print(f'[{code}] trends copied from curated project', flush=True)
            continue
        if only and code not in only.split(','):
            continue
        out = {}
        ok = True
        for key, field, extra in STEPS:
            flt = f'institutions.id:{oid},from_publication_date:{START},to_publication_date:{END}{extra}'
            url = ('https://api.openalex.org/works?filter=' + urllib.parse.quote(flt, safe=':,|')
                   + f'&group_by={field}&per_page=200&api_key={KEY}')
            d = get(url)
            if d is None:
                print(f'[{code}] {key}: failed', flush=True)
                ok = False
                break
            if d.get('__quota__'):
                print(f'[{code}] {key}: QUOTA', flush=True)
                return
            out[key] = [{'key': g['key'], 'name': g['key_display_name'], 'count': g['count']}
                        for g in d.get('group_by', [])]
            time.sleep(0.25)
        if ok:
            json.dump(out, open(out_path, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
            print(f'[{code}] trends saved ({sum(len(v) for v in out.values())} groups)', flush=True)


if __name__ == '__main__':
    main()
