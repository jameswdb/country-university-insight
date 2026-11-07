# -*- coding: utf-8 -*-
"""Derived cross-university indicators.

Adds to each analysis.json a `derived` block and to each faculty.json the PI
signal and a rising-star flag:

  concentration   top-10% of A-tier researchers' share of the university's output
  specialisation  domain share vs the ten-university average (>1.3 distinctive)
  rising stars    A-tier whose recent 3-year rate is >=1.8x their 2016-2020 rate
  pi              last-author share (sampled top-cited works), median by tier
"""
import json, io, os, sys, glob, statistics, collections

if __name__ == '__main__':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONF = json.load(open(os.path.join(ROOT, 'config', 'universities.json'), encoding='utf-8'))
PROC = os.path.join(ROOT, 'data', 'processed')


def load_pi(code):
    p = os.path.join(PROC, code, 'pi.jsonl')
    out = {}
    if os.path.exists(p):
        for line in open(p, encoding='utf-8'):
            try:
                r = json.loads(line)
                out[r['id']] = r
            except Exception:
                pass
    return out


def main():
    analyses, facs = {}, {}
    for uni in CONF['universities']:
        code = uni['code']
        ap = os.path.join(PROC, code, 'analysis.json')
        fp = os.path.join(PROC, code, 'faculty.json')
        if not (os.path.exists(ap) and os.path.exists(fp)):
            continue
        analyses[code] = json.load(open(ap, encoding='utf-8'))
        facs[code] = json.load(open(fp, encoding='utf-8'))

    # ---- ten-university domain shares (for specialisation)
    tot_w = sum(a['counts']['works_10y'] for a in analyses.values()) or 1
    dom_w = collections.Counter()
    for a in analyses.values():
        for f in a['faculties']:
            dom_w[f['domain_en']] += f['works']
    ten_share = {d: v / tot_w for d, v in dom_w.items()}

    for code, A in analyses.items():
        rows = facs[code]
        pi = load_pi(code)
        for r in rows:
            sig = pi.get(r.get('id'))
            r['last_share'] = sig['last_share'] if sig else None
            r['pi_sampled'] = sig['sampled'] if sig else 0
            early, recent = r.get('works_2016_2020') or 0, r.get('works_2024_2026') or 0
            rate_early = early / 5.0
            rate_recent = recent / 3.0
            r['rising'] = bool(r.get('tier') == 'A' and recent >= 5 and rate_early > 0
                               and rate_recent >= 1.8 * rate_early)
            w = r.get('works_total') or 0
            c = r.get('cited') or 0
            r['cite_per_work'] = round(c / w, 2) if w else None

        a_rows = [r for r in rows if r.get('tier') == 'A' and (r.get('works_10y') or 0) > 0]
        a_rows.sort(key=lambda x: -(x['works_10y'] or 0))
        total_a = sum(r['works_10y'] for r in a_rows) or 1
        k = max(1, int(len(a_rows) * 0.1))
        top10 = sum(r['works_10y'] for r in a_rows[:k])
        concentration = {
            'top10pct_share': round(top10 / total_a, 3),
            'top10pct_n': k,
            'a_tier_output': total_a,
            'median_output': round(statistics.median([r['works_10y'] for r in a_rows]), 1) if a_rows else 0,
        }

        spec = []
        for f in A['faculties']:
            share = f['works'] / (A['counts']['works_10y'] or 1)
            base = ten_share.get(f['domain_en'], 0)
            spec.append({'domain_en': f['domain_en'], 'domain_zh': f['domain_zh'],
                         'share': round(share, 3), 'ten_share': round(base, 3),
                         'index': round(share / base, 2) if base else None,
                         'n': f['n'], 'works': f['works']})
        spec.sort(key=lambda x: -(x['index'] or 0))

        stars = [r for r in a_rows if r.get('rising')]
        stars.sort(key=lambda x: -(x.get('works_2024_2026') or 0))

        by_tier = collections.defaultdict(list)
        for r in rows:
            if r.get('last_share') is not None:
                by_tier[r.get('tier')].append(r['last_share'])
        all_shares = [s for v in by_tier.values() for s in v]
        a_shares = by_tier.get('A', [])
        pi_stats = {
            'n': len(all_shares),
            'n_A': len(a_shares),
            # headline number is the A-tier median: the pooled median is dragged
            # down by the deliberately sampled C-tier control group
            'median': round(statistics.median(a_shares), 3) if a_shares else None,
            'median_all': round(statistics.median(all_shares), 3) if all_shares else None,
            'by_tier': {t: {'n': len(v), 'median': round(statistics.median(v), 3)}
                        for t, v in by_tier.items() if v},
        }

        oc = collections.Counter(r.get('orcid_role_class') for r in rows
                                 if r.get('orcid_role_class'))
        n_oc = sum(oc.values())
        A['derived'] = {
            'orcid_check': {'n': n_oc,
                            'professor': oc.get('professor', 0),
                            'associate': oc.get('associate', 0),
                            'lecturer': oc.get('lecturer', 0),
                            'postdoc': oc.get('postdoc', 0),
                            'student': oc.get('student', 0),
                            'other': oc.get('other', 0)},
            'concentration': concentration,
            'specialisation': spec,
            'rising_stars': [{'name': r['name'], 'domain': r.get('domain_en'),
                              'recent': r.get('works_2024_2026'), 'early': r.get('works_2016_2020'),
                              'works': r.get('works_10y'), 'url': r.get('url')}
                             for r in stars[:15]],
            'pi': pi_stats,
            'cite_per_work_median': round(statistics.median(
                [r['cite_per_work'] for r in rows if r.get('cite_per_work')]), 2)
                if any(r.get('cite_per_work') for r in rows) else None,
        }
        json.dump(A, open(os.path.join(PROC, code, 'analysis.json'), 'w', encoding='utf-8'),
                  ensure_ascii=False, indent=1)
        json.dump(rows, open(os.path.join(PROC, code, 'faculty.json'), 'w', encoding='utf-8'),
                  ensure_ascii=False, indent=1)
        print(f'[{code}] top10% share={concentration["top10pct_share"]:.0%} '
              f'stars={len(stars)} pi_median={pi_stats["median"]} '
              f'spec_top={spec[0]["domain_en"]}({spec[0]["index"]})', flush=True)

    # ten-university ranking table for the comparison chapter
    rank = []
    for code, A in analyses.items():
        C = A['counts']
        A_rows = [r for r in facs[code] if r.get('tier') == 'A']
        rank.append({
            'code': code, 'name_zh': A['name_zh'], 'name_en': A['name_en'],
            'population': C['population'], 'tier_A': C['tier_A'],
            'works': C['works_10y'], 'recent': C['works_recent'],
            'growth': A['baseline_growth'],
            'per_capita_A': round(C['works_10y'] / max(1, C['tier_A']), 1),
            'top10_share': A['derived']['concentration']['top10pct_share'],
            'pi_median': A['derived']['pi']['median'],
            'inst_works': C['institution_works_10y'],
        })
    json.dump(rank, open(os.path.join(PROC, '_ten_ranking.json'), 'w', encoding='utf-8'),
              ensure_ascii=False, indent=1)
    print('[derive] ten ranking written')


if __name__ == '__main__':
    main()
