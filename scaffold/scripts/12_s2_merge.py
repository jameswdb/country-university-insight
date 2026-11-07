# -*- coding: utf-8 -*-
"""Merge Semantic Scholar results into each university's faculty table.

Reads data/raw/s2/<CODE>.jsonl and adds:
  s2_id, s2_papers, s2_citations, s2_hindex,
  s2_influential, s2_infl_per_paper, s2_cite_per_paper,
  s2_top_title, s2_top_tldr, s2_top_influential
"""
import json, io, os, sys, glob

if __name__ == '__main__':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONF = json.load(open(os.path.join(ROOT, 'config', 'universities.json'), encoding='utf-8'))
PROC = os.path.join(ROOT, 'data', 'processed')
RAW = os.path.join(ROOT, 'data', 'raw', 's2')


def main():
    total = matched = 0
    for uni in CONF['universities']:
        code = uni['code']
        fp = os.path.join(PROC, code, 'faculty.json')
        sp = os.path.join(RAW, f'{code}.jsonl')
        if not (os.path.exists(fp) and os.path.exists(sp)):
            continue
        by_key = {}
        for line in open(sp, encoding='utf-8'):
            try:
                d = json.loads(line)
                by_key[d['key']] = d
            except Exception:
                pass
        rows = json.load(open(fp, encoding='utf-8'))
        n = 0
        for r in rows:
            d = by_key.get(r.get('id') or r.get('name'))
            if not d or not d.get('s2'):
                continue
            s2 = d['s2']
            r['s2_id'] = s2.get('authorId')
            r['s2_papers'] = s2.get('paperCount')
            r['s2_citations'] = s2.get('citationCount')
            r['s2_hindex'] = s2.get('hIndex')
            infl = d.get('influential_sum')
            r['s2_influential'] = infl
            sampled = d.get('papers_sampled') or 0
            r['s2_infl_per_paper'] = round(infl / sampled, 2) if (infl is not None and sampled) else None
            r['s2_cite_per_paper'] = (round(s2['citationCount'] / s2['paperCount'], 1)
                                      if s2.get('citationCount') and s2.get('paperCount') else None)
            tp = (d.get('top_papers') or [{}])[0]
            r['s2_top_title'] = tp.get('title')
            r['s2_top_tldr'] = tp.get('tldr')
            r['s2_top_influential'] = tp.get('influential')
            n += 1
        json.dump(rows, open(fp, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
        total += len(rows)
        matched += n
        print(f'[{code}] merged {n}/{len(rows)}', flush=True)
    print(f'[s2-merge] {matched} rows enriched out of {total}', flush=True)


if __name__ == '__main__':
    main()
