# -*- coding: utf-8 -*-
"""Discover a country's leading research universities from OpenAlex and write the
pipeline config.

Ranking basis (stated explicitly, because "top" is not self-evident):
  * OpenAlex `works_count` for the institution  -> research output volume
  * type:education, country_code:<ISO2>
  * sub-institutions, funds, hospitals and "friends of" entities are filtered out
The user is shown the resulting table and may replace any entry before the
expensive stages run.

Usage
  python scripts/00_discover.py --country IL --top 10
  python scripts/00_discover.py --country "Netherlands" --top 12 --out config/universities.json

Writes config/universities.json in the same shape the rest of the pipeline expects:
  {code, name_en, name_zh, openalex_id, ror, city, roster: "openalex", note}
"""
import argparse, json, io, os, ssl, sys, urllib.error, urllib.parse, urllib.request

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
KEY = os.environ.get('OPENALEX_API_KEY', '').strip()
BASE = 'https://api.openalex.org'
CTX = ssl.create_default_context()
CTX.check_hostname = False
CTX.verify_mode = ssl.CERT_NONE
UA = {'User-Agent': 'country-university-insight/1.0 (academic research)'}

# noise that OpenAlex sometimes types as education institutions
NOISE = ('friends of', 'american committee', 'canadian friends', 'society',
         'foundation', 'fund', 'hospital', 'medical center', 'college of',
         'school of', 'institute of technology transfer')


def get(path, params):
    q = urllib.parse.urlencode(params)
    url = f'{BASE}{path}?{q}'
    if KEY:
        url += f'&api_key={KEY}'
    for i in range(3):
        try:
            r = urllib.request.urlopen(urllib.request.Request(url, headers=UA),
                                       timeout=60, context=CTX)
            return json.loads(r.read().decode('utf-8'))
        except urllib.error.HTTPError as e:
            if e.code in (403, 429):
                raise SystemExit(f'OpenAlex quota/permission problem: {e.code} '
                                 f'(set OPENALEX_API_KEY and retry)')
            raise
        except Exception:
            import time
            time.sleep(2 * (i + 1))
    raise SystemExit('OpenAlex request failed')


STOP = {'of', 'the', 'and', 'for', 'at', 'in', 'on', 'de', 'van', 'der'}


def code_for(name, used):
    """Readable short code from the words: 'University of Amsterdam' -> 'UA'."""
    words = [w for w in ''.join(c if c.isalnum() or c == ' ' else ' '
                                for c in name).split() if w.lower() not in STOP]
    if len(words) >= 2:
        base = ''.join(w[0] for w in words).upper()[:4]
    else:
        base = (words[0][:5].upper() if words else 'UNI')
    code, n = base, 1
    while code in used:
        n += 1
        code = f'{base[:3]}{n}'
    used.add(code)
    return code


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--country', required=True,
                    help='country name or ISO-2 code, e.g. IL / Israel / Netherlands')
    ap.add_argument('--top', type=int, default=10)
    ap.add_argument('--out', default=os.path.join(ROOT, 'config', 'universities.json'))
    args = ap.parse_args()

    c = args.country.strip()
    iso = c.upper() if len(c) == 2 else c
    d = get('/institutions', {
        'filter': f'country_code:{iso},type:education',
        'sort': 'works_count:desc',
        'per_page': 50,
        'select': 'id,display_name,ror,works_count,cited_by_count,geo,lineage,type',
    })
    rows = []
    for r in d.get('results', []):
        name = r['display_name']
        if any(k in name.lower() for k in NOISE):
            continue
        rows.append({
            'openalex_id': r['id'].rsplit('/', 1)[-1],
            'name_en': name,
            'ror': r.get('ror'),
            'works': r.get('works_count') or 0,
            'city': (r.get('geo') or {}).get('city') or '',
        })
    rows = rows[:args.top]
    if not rows:
        raise SystemExit(f'no institutions found for {args.country!r}')

    used = set()
    unis = []
    for r in rows:
        unis.append({
            'code': code_for(r['name_en'], used),
            'name_en': r['name_en'],
            'name_zh': r['name_en'],          # replace with a Chinese name if you have one
            'openalex_id': r['openalex_id'],
            'ror': r['ror'],
            'city': r['city'],
            'roster': 'openalex',
            'note': 'OpenAlex 署名口径；无公开统一人员名录时使用',
        })

    conf = {
        'country': c,
        'selection_basis': (f'OpenAlex 中 country_code={iso}、type=education 的机构，'
                            '按 works_count 排序取前 %d；已剔除基金会、医院、friends-of 等非大学实体' % len(unis)),
        'ranking_source': ['OpenAlex institutions API (works_count, 2026 snapshot)'],
        'universities': unis,
    }
    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    json.dump(conf, open(args.out, 'w', encoding='utf-8'), ensure_ascii=False, indent=2)

    print(f'country: {c}   universities: {len(unis)}   -> {args.out}')
    print(f'{"code":8s} {"works":>8s}  {"city":16s} name')
    for u, r in zip(unis, rows):
        print(f'{u["code"]:8s} {r["works"]:8,d}  {u["city"][:16]:16s} {u["name_en"]}')
    print('\nReview this list with the user before running the download stage.')
    print('Any entry can be replaced by editing the JSON (same shape).')


if __name__ == '__main__':
    main()
