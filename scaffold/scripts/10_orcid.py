# -*- coding: utf-8 -*-
"""ORCID enrichment: career history, current position and degrees.

LinkedIn is not usable for bulk enrichment (no login, and its terms forbid
automated access). ORCID is the legitimate equivalent: it is public, person-owned
and explicitly offers an API. For every A-tier researcher with an ORCID iD we pull
`/employments` and `/educations`, which give positions (organisation, role,
department, years) and degrees.

Output: insight/data/raw/orcid/<orcid>.json      (cache, one file per person)
        insight/data/processed/<CODE>/faculty.json  (fields added in place)
"""
import urllib.request, urllib.error, ssl, json, io, os, sys, time, glob
from concurrent.futures import ThreadPoolExecutor, as_completed

if __name__ == '__main__':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONF = json.load(open(os.path.join(ROOT, 'config', 'universities.json'), encoding='utf-8'))
PROC = os.path.join(ROOT, 'data', 'processed')
CACHE = os.path.join(ROOT, 'data', 'raw', 'orcid')
os.makedirs(CACHE, exist_ok=True)
TAU_RAW = r'D:\dev\University-IL\data\raw\openalex'

CTX = ssl.create_default_context()
CTX.check_hostname = False
CTX.verify_mode = ssl.CERT_NONE
H = {'Accept': 'application/json', 'User-Agent': 'IsraelInsight/1.0 (academic research)'}
WORKERS = int(os.environ.get('WORKERS', '8'))
MIN_WORKS = int(os.environ.get('MIN_WORKS', '15'))


def get(url, tries=3):
    for i in range(tries):
        try:
            r = urllib.request.urlopen(urllib.request.Request(url, headers=H), timeout=30, context=CTX)
            return json.loads(r.read().decode('utf-8'))
        except urllib.error.HTTPError as e:
            if e.code == 404:
                return {'__missing__': True}
            if e.code in (429, 503):
                time.sleep(2 * (i + 1))
            else:
                time.sleep(0.8 * (i + 1))
        except Exception:
            time.sleep(0.8 * (i + 1))
    return None


def parse_affiliations(payload):
    out = []
    for grp in (payload or {}).get('affiliation-group', []) or []:
        for s in grp.get('summaries', []) or []:
            for k, v in s.items():
                if not isinstance(v, dict):
                    continue
                org = (v.get('organization') or {})
                addr = (v.get('organization-address') or {})
                sd = (v.get('start-date') or {}) or {}
                ed = (v.get('end-date') or {}) or {}
                out.append({
                    'organization': org.get('name'),
                    'role': v.get('role-title') or v.get('department-name'),
                    'department': v.get('department-name'),
                    'city': addr.get('city'),
                    'country': addr.get('country'),
                    'start': (sd.get('year') or {}).get('value') if isinstance(sd, dict) else None,
                    'end': (ed.get('year') or {}).get('value') if isinstance(ed, dict) else None,
                })
    return [a for a in out if a['organization']]


def fetch(orcid):
    p = os.path.join(CACHE, f'{orcid}.json')
    if os.path.exists(p):
        try:
            return json.load(open(p, encoding='utf-8'))
        except Exception:
            pass
    emp = get(f'https://pub.orcid.org/v3.0/{orcid}/employments')
    edu = get(f'https://pub.orcid.org/v3.0/{orcid}/educations')
    if emp is None and edu is None:
        return None
    rec = {'orcid': orcid,
           'employments': parse_affiliations(emp) if emp and not emp.get('__missing__') else [],
           'educations': parse_affiliations(edu) if edu and not edu.get('__missing__') else []}
    json.dump(rec, open(p, 'w', encoding='utf-8'), ensure_ascii=False)
    return rec


ROLE_RULES = [
    ('postdoc', ('postdoc', 'post-doc', 'post doctoral', 'post-doctoral', 'research fellow',
                 'postdoctoral')),
    ('student', ('phd student', 'doctoral student', 'graduate student', 'm.sc', 'msc student')),
    ('professor', ('professor', 'prof.', 'chair professor', 'full professor')),
    ('associate', ('associate professor', 'senior lecturer')),
    ('lecturer', ('lecturer', 'senior teacher', 'teacher', 'instructor')),
    ('research', ('research scientist', 'researcher', 'research associate', 'principal investigator')),
]


def role_class(text):
    t = (text or '').lower()
    for name, keys in ROLE_RULES:
        if any(k in t for k in keys):
            return name
    return 'other'


def backfill_tau():
    """TAU rows had no ORCID because the curated table dropped the field."""
    p = os.path.join(PROC, 'TAU', 'faculty.json')
    if not os.path.exists(p):
        return
    rows = json.load(open(p, encoding='utf-8'))
    id2orcid = {}
    for f in glob.glob(os.path.join(TAU_RAW, '*', '*', '*.json')):
        try:
            d = json.load(open(f, encoding='utf-8'))
        except Exception:
            continue
        for a in d.get('results', []):
            o = (a.get('orcid') or '').replace('https://orcid.org/', '')
            if o:
                id2orcid[a['id'].rsplit('/', 1)[-1]] = o
    n = 0
    for r in rows:
        if not r.get('orcid') and r.get('id') in id2orcid:
            r['orcid'] = id2orcid[r['id']]
            n += 1
    json.dump(rows, open(p, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print(f'[orcid] TAU backfilled {n} ORCIDs', flush=True)


def main():
    backfill_tau()
    targets = {}
    for uni in CONF['universities']:
        code = uni['code']
        p = os.path.join(PROC, code, 'faculty.json')
        if not os.path.exists(p):
            continue
        rows = json.load(open(p, encoding='utf-8'))
        for r in rows:
            if r.get('tier') != 'A' or not r.get('orcid'):
                continue
            if (r.get('works_10y') or 0) < MIN_WORKS:
                continue
            targets.setdefault(r['orcid'], []).append((code, r))
    print(f'[orcid] targets={len(targets)} (A-tier, works>={MIN_WORKS})', flush=True)

    todo = [o for o in targets if not os.path.exists(os.path.join(CACHE, f'{o}.json'))]
    print(f'[orcid] cached={len(targets) - len(todo)} todo={len(todo)}', flush=True)
    t0 = time.time()
    done = 0
    if os.environ.get('MERGE_ONLY'):
        todo = []
    with ThreadPoolExecutor(max_workers=WORKERS) as ex:
        futs = {ex.submit(fetch, o): o for o in todo}
        for fut in as_completed(futs):
            o = futs[fut]
            try:
                fut.result()
            except Exception:
                pass
            done += 1
            if done % 500 == 0:
                print(f'[orcid] {done}/{len(todo)} t={time.time()-t0:.0f}s', flush=True)

    # merge into faculty rows
    merged = 0
    for uni in CONF['universities']:
        code = uni['code']
        p = os.path.join(PROC, code, 'faculty.json')
        if not os.path.exists(p):
            continue
        rows = json.load(open(p, encoding='utf-8'))
        for r in rows:
            o = r.get('orcid')
            if not o:
                continue
            cp = os.path.join(CACHE, f'{o}.json')
            if not os.path.exists(cp):
                continue
            rec = json.load(open(cp, encoding='utf-8'))
            emps = rec.get('employments') or []
            edus = rec.get('educations') or []
            def _yr(v):
                try:
                    return int(v)
                except (TypeError, ValueError):
                    return 9999
            emps.sort(key=lambda e: -_yr(e.get('end')))
            current = next((e for e in emps if not e.get('end')), emps[0] if emps else None)
            r['orcid_current'] = (f"{current.get('role') or ''} @ {current['organization']}"
                                  if current else None)
            r['orcid_history'] = '; '.join(
                f"{e.get('organization')}"
                + (f"（{e.get('start')}-{e.get('end') or '今'}）" if e.get('start') or e.get('end') else '')
                for e in emps[:4]) or None
            raw_role = ' '.join(filter(None, [current.get('role') if current else None,
                                              current.get('department') if current else None]))
            r['orcid_role_class'] = role_class(raw_role) if current else None
            r['orcid_degrees'] = '; '.join(
                f"{e.get('role') or ''} {e.get('organization') or ''}".strip() for e in edus[:3]) or None
            if r['orcid_current'] or r['orcid_history']:
                merged += 1
        json.dump(rows, open(p, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print(f'[orcid] merged career data into {merged} rows', flush=True)


if __name__ == '__main__':
    main()
