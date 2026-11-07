# -*- coding: utf-8 -*-
"""Per-university analysis: population, tiers, domains, trends, notable people.

TAU and Technion are re-ingested from their curated project outputs so the ten
universities share one schema while keeping their provenance ("official roster"
vs "OpenAlex inferred").

Output: insight/data/processed/<CODE>/analysis.json
        insight/data/processed/<CODE>/faculty.json
"""
import json, io, os, sys, glob, collections

if __name__ == '__main__':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, 'scripts'))
from domains import domain_of, classify, DOMAIN_EN, DOMAIN_ZH, TIER_ZH

CONF = json.load(open(os.path.join(ROOT, 'config', 'universities.json'), encoding='utf-8'))
YEARS = list(range(2016, 2027))
FAC_EN = {'exact': 'Exact Sciences', 'eng': 'Engineering', 'life': 'Life Sciences',
          'med': 'Medical & Health Sciences', 'neuro': 'Neuroscience',
          'soc': 'Social Sciences', 'hum': 'Humanities', 'arts': 'Arts',
          'law': 'Law', 'mgmt': 'Management', 'env': 'Environment & Earth Sciences',
          'inter': 'Interdisciplinary', 'other': 'Other'}
FAC_ZH = {'exact': '精确科学', 'eng': '工程', 'life': '生命科学', 'med': '医学与健康',
          'neuro': '神经科学', 'soc': '社会科学', 'hum': '人文', 'arts': '艺术',
          'law': '法学', 'mgmt': '管理学', 'env': '环境与地球科学',
          'inter': '跨学科', 'other': '其他'}


def activity(w):
    if w >= 60:
        return '非常活跃'
    if w >= 20:
        return '活跃'
    if w >= 5:
        return '中等'
    if w >= 1:
        return '低活跃'
    return '无近十年论文'


def load_openalex(oid):
    prof = {}
    for f in glob.glob(os.path.join(ROOT, 'data', 'raw', oid, '*.json')):
        if os.path.basename(f) == 'state.json':
            continue
        for a in json.load(open(f, encoding='utf-8')).get('results', []):
            aid = a['id'].rsplit('/', 1)[-1]
            yb = {}
            for y in (a.get('counts_by_year') or []):
                if y.get('works_count'):
                    yb[int(y['year'])] = y['works_count']
            ys = [y for y, v in yb.items() if v]
            prof[aid] = {
                'id': aid, 'name': a['display_name'],
                'orcid': (a.get('orcid') or '').replace('https://orcid.org/', '') or None,
                'works_total': a.get('works_count') or 0,
                'cited': a.get('cited_by_count') or 0,
                'h': (a.get('summary_stats') or {}).get('h_index'),
                'span': (max(ys) - min(ys) + 1) if ys else 0,
                'years': yb,
                'topics': [{'name': t.get('display_name'), 'count': t.get('count')}
                           for t in (a.get('topics') or [])[:8]],
                'insts': [x.get('display_name') for x in (a.get('last_known_institutions') or [])],
            }
    return prof


def build_rows(prof):
    rows = []
    for aid, a in prof.items():
        if a['works_total'] < 6:
            continue
        y10 = {y: v for y, v in a['years'].items() if 2016 <= y <= 2026}
        w10 = sum(y10.values())
        dom = domain_of(a['topics'])
        rows.append({
            **a,
            'works_10y': w10,
            'works_2016_2020': sum(v for y, v in y10.items() if y <= 2020),
            'works_2021_2026': sum(v for y, v in y10.items() if y >= 2021),
            'works_2024_2026': sum(v for y, v in y10.items() if y >= 2024),
            'activity': activity(w10),
            'tier': classify(a['works_total'], a['span']),
            'domain': dom, 'domain_en': DOMAIN_EN.get(dom, dom), 'domain_zh': DOMAIN_ZH.get(dom, dom),
            'top_topics': [t['name'] for t in a['topics'][:5]],
            'url': f'https://openalex.org/{aid}',
        })
    rows.sort(key=lambda r: (r['tier'], -r['works_10y']))
    return rows


def load_existing(uni):
    """Re-ingest TAU / Technion curated tables into the shared schema."""
    code = uni['code']
    if code == 'TAU':
        src = json.load(open(uni['existing_data'], encoding='utf-8'))
        # map the official faculty labels onto the shared domain taxonomy
        FAC2DOM = {'Exact Sciences': 'physics', 'Engineering': 'engineering',
                   'Life Sciences': 'life sciences', 'Medical & Health Sciences': 'medicine',
                   'Neuroscience': 'neuroscience', 'Social Sciences': 'social sciences',
                   'Humanities': 'humanities', 'Arts': 'humanities', 'Law': 'law',
                   'Management': 'management', 'Environment & Earth Sciences': 'environment',
                   'Interdisciplinary': 'other', 'Other': 'other'}
        RANK2TIER = {'professor': 'A', 'associate_professor': 'A',
                     'senior_lecturer': 'B', 'lecturer_phd': 'B', 'lecturer': 'C'}
        rows = []
        for p in src:
            topics = [{'name': t} for t in (p.get('top_topics') or '').split('; ') if t]
            dom = domain_of(topics) if topics else FAC2DOM.get(p.get('faculty_en'), 'other')
            rows.append({
                'id': p.get('openalex_id') or '', 'name': p.get('name_en') or p.get('name_he'),
                'name_he': p.get('name_he'), 'orcid': None,
                'works_total': p.get('works_total') or 0, 'cited': None, 'h': None,
                'span': None, 'years': p.get('years') or {},
                'topics': [{'name': t} for t in (p.get('top_topics') or '').split('; ') if t][:8],
                'insts': [], 'works_10y': p.get('works_10y'),
                'works_2016_2020': p.get('works_2016_2020') or 0,
                'works_2021_2026': p.get('works_2021_2026') or 0,
                'works_2024_2026': p.get('works_2024_2026') or 0,
                'activity': p.get('activity') or activity(p.get('works_10y') or 0),
                'tier': RANK2TIER.get(p.get('rank'), 'C'),
                'domain': dom, 'domain_en': DOMAIN_EN.get(dom, dom),
                'domain_zh': DOMAIN_ZH.get(dom, dom),
                'rank_zh': p.get('rank_zh'), 'match_confidence': p.get('match_confidence'),
                'role_he': p.get('role_he'),
                'top_topics': (p.get('top_topics') or '').split('; ')[:5],
                'faculty_en_official': p.get('faculty_en'),
                'url': p.get('url') or '',
            })
        return rows, 'official'

    src = json.load(open(uni['existing_data'], encoding='utf-8'))
    TECH2DOM = {'eng': 'engineering', 'life': 'life sciences', 'med': 'medicine',
                'neuro': 'neuroscience', 'phys': 'physics', 'chem': 'chemistry',
                'materials': 'materials', 'cs': 'computer science', 'math': 'mathematics',
                'arch': 'architecture', 'env': 'environment', 'hum': 'humanities',
                'soc': 'social sciences', 'mgmt': 'management', 'law': 'law',
                'inter': 'other', 'other': 'other', 'exact': 'other',
                'cheng': 'engineering', 'aero': 'engineering', 'civil': 'engineering',
                'mech': 'engineering', 'ee': 'engineering', 'ind': 'management',
                'bme': 'engineering', 'biotech': 'engineering'}
    rows = []
    for p in src:
        rows.append({
            'id': p['id'], 'name': p['name'], 'name_he': None, 'orcid': p.get('orcid'),
            'works_total': p.get('works_total') or 0, 'cited': p.get('cited_total'), 'h': p.get('h'),
            'span': p.get('span'), 'years': p.get('years') or {},
            'topics': p.get('top_topics_detail') or [{'name': t} for t in p.get('top_topics') or []],
            'insts': p.get('insts') or [], 'works_10y': p.get('works_10y'),
            'works_2016_2020': p.get('works_2016_2020') or 0,
            'works_2021_2026': p.get('works_2021_2026') or 0,
            'works_2024_2026': p.get('works_2024_2026') or 0,
            'activity': p.get('activity') or activity(p.get('works_10y') or 0),
            'tier': p.get('tier') or 'C',
            'domain': TECH2DOM.get(p.get('faculty'), p.get('faculty')),
            'domain_en': DOMAIN_EN.get(TECH2DOM.get(p.get('faculty'), 'other')),
            'domain_zh': DOMAIN_ZH.get(TECH2DOM.get(p.get('faculty'), 'other')),
            'top_topics': p.get('top_topics') or [],
            'url': p.get('url') or '',
        })
    return rows, 'openalex'


def analyse(uni):
    code = uni['code']
    outdir = os.path.join(ROOT, 'data', 'processed', code)
    os.makedirs(outdir, exist_ok=True)
    if uni.get('existing_data') and os.path.exists(uni['existing_data']):
        rows, provenance = load_existing(uni)
    else:
        rows, provenance = build_rows(load_openalex(code)), 'openalex'

    trends = json.load(open(os.path.join(outdir, 'institution_trends.json'), encoding='utf-8'))
    yrs = {int(g['key']): g['count'] for g in trends.get('years', []) if str(g['key']).isdigit()}
    early = {g['name']: g['count'] for g in trends.get('early_topics', [])}
    late = {g['name']: g['count'] for g in trends.get('late_topics', [])}
    et, lt = sum(early.values()), sum(late.values())
    mig = []
    for t in set(early) & set(late):
        e, l = early[t], late[t]
        if e < 15 or l < 15:
            continue
        mig.append({'topic': t, 'early': e, 'late': l,
                    'rel_growth': round((((l + 5) / lt) / ((e + 5) / et) - 1) * 100, 1)})
    mig.sort(key=lambda r: -r['rel_growth'])

    # domain aggregates
    fac = collections.defaultdict(lambda: {'n': 0, 'A': 0, 'B': 0, 'C': 0, 'works': 0,
                                           'early': 0, 'late': 0, 'recent': 0})
    for r in rows:
        key = r.get('domain') or 'other'
        f = fac[key]
        f['n'] += 1
        f[r['tier']] = f.get(r['tier'], 0) + 1
        f['works'] += r['works_10y'] or 0
        f['early'] += r['works_2016_2020'] or 0
        f['late'] += r['works_2021_2026'] or 0
        f['recent'] += r['works_2024_2026'] or 0
    faculties = []
    for k, v in fac.items():
        g = (v['late'] - v['early']) / v['early'] * 100 if v['early'] else None
        faculties.append({'domain': k, 'domain_en': DOMAIN_EN.get(k, k), 'domain_zh': DOMAIN_ZH.get(k, k),
                          'n': v['n'], 'A': v['A'], 'B': v['B'], 'C': v['C'],
                          'works': v['works'], 'works_early': v['early'], 'works_late': v['late'],
                          'growth_pct': round(g, 1) if g is not None else None,
                          'works_recent': v['recent'],
                          'per_capita': round(v['works'] / v['n'], 1) if v['n'] else 0})
    faculties.sort(key=lambda x: -x['n'])

    pop = len(rows)
    a = sum(1 for r in rows if r['tier'] == 'A')
    b = sum(1 for r in rows if r['tier'] == 'B')
    c = sum(1 for r in rows if r['tier'] == 'C')
    w10 = sum(r['works_10y'] or 0 for r in rows)
    recent = sum(r['works_2024_2026'] or 0 for r in rows)
    oa = {g['name']: g['count'] for g in trends.get('open_access', [])}

    pop_rows = [r for r in rows if (r['works_10y'] or 0) > 0]
    top_out = sorted(pop_rows, key=lambda x: -(x['works_10y'] or 0))[:30]
    top_rec = sorted(pop_rows, key=lambda x: -(x['works_2024_2026'] or 0))[:30]

    def slim(r):
        return {'name': r['name'], 'name_he': r.get('name_he'),
                'domain': r.get('domain_en') or '', 'works': r['works_10y'],
                'recent': r['works_2024_2026'], 'tier': r['tier'],
                'topics': (r.get('top_topics') or [])[:3], 'url': r.get('url') or ''}

    analysis = {
        'code': code, 'name_en': uni['name_en'], 'name_zh': uni['name_zh'],
        'name_he': uni.get('name_he'), 'ror': uni.get('ror'), 'city': uni.get('city'),
        'openalex_id': uni['openalex_id'], 'provenance': provenance, 'note': uni.get('note', ''),
        'inst_years': {str(y): yrs.get(y, 0) for y in YEARS},
        'inst_types': {g['name']: g['count'] for g in trends.get('types', [])},
        'open_access': {'oa': oa.get('true', 0), 'total': sum(oa.values())},
        'countries': [{'name': g['name'], 'count': g['count']} for g in trends.get('countries', [])[:15]],
        'topics': [{'name': g['name'], 'count': g['count']} for g in trends.get('topics', [])[:20]],
        'topic_migration': mig,
        'baseline_growth': round((lt / et - 1) * 100, 1) if et else None,
        'faculties': faculties,
        'counts': {'population': pop, 'tier_A': a, 'tier_B': b, 'tier_C': c,
                   'works_10y': w10, 'works_recent': recent,
                   'institution_works_10y': sum(yrs.values())},
        'top_output': [slim(r) for r in top_out],
        'top_recent': [slim(r) for r in top_rec],
    }
    json.dump(analysis, open(os.path.join(outdir, 'analysis.json'), 'w', encoding='utf-8'),
              ensure_ascii=False, indent=1)
    json.dump(rows, open(os.path.join(outdir, 'faculty.json'), 'w', encoding='utf-8'),
              ensure_ascii=False, indent=1)
    print(f'[{code}] pop={pop} A={a} B={b} C={c} works10y={w10} growth={analysis["baseline_growth"]}% '
          f'domains={len(faculties)}', flush=True)
    return analysis


def main():
    only = os.environ.get('UNIS', '').strip()
    for uni in CONF['universities']:
        if only and uni['code'] not in only.split(','):
            continue
        try:
            analyse(uni)
        except Exception as e:
            print(f'[{uni["code"]}] FAILED: {type(e).__name__}: {e}', flush=True)


if __name__ == '__main__':
    main()
