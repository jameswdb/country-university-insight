# -*- coding: utf-8 -*-
"""Per-university figures (6 each) into out/figs/<CODE>/."""
import json, io, os, sys

if __name__ == '__main__':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, 'scripts'))
import charts

CONF = json.load(open(os.path.join(ROOT, 'config', 'universities.json'), encoding='utf-8'))
PROC = os.path.join(ROOT, 'data', 'processed')
FIGS = os.path.join(ROOT, 'out', 'figs')
YEARS = [str(y) for y in range(2016, 2027)]


def build(uni):
    code = uni['code']
    A = json.load(open(os.path.join(PROC, code, 'analysis.json'), encoding='utf-8'))
    d = os.path.join(FIGS, code)
    os.makedirs(d, exist_ok=True)
    zh = uni['name_zh']
    fac = A['faculties']

    charts.line_multi({'全校论文数': [A['inst_years'].get(y, 0) for y in YEARS]}, YEARS,
                      f'{zh} 年度论文产出（2016–2026）',
                      '口径：OpenAlex 署名该校的论文；2026 年收录尚不完整',
                      os.path.join(d, 'years.png'))

    charts.bars_h([(x['domain_en'], x['n']) for x in fac],
                  f'{zh} 各研究领域人数（A/B/C 合计）',
                  f"研究人口 {A['counts']['population']:,} 人（≥6 篇论文）",
                  os.path.join(d, 'domains.png'), top=14)

    charts.bars_h([(x['domain_en'], x['works']) for x in sorted(fac, key=lambda z: -z['works'])],
                  f'{zh} 各领域近十年论文总量',
                  f"可归属合计 {A['counts']['works_10y']:,} 篇", os.path.join(d, 'works.png'), top=14)

    charts.bars_v_grouped([x['domain_en'] for x in fac[:10]],
                          {'2016–2020': [x['works_early'] for x in fac[:10]],
                           '2021–2026': [x['works_late'] for x in fac[:10]]},
                          f'{zh} 各领域前后五年产出对比', '右柱高于左柱＝该领域近五年在扩张',
                          os.path.join(d, 'growth.png'), legend_y=160)

    mig = A['topic_migration']
    risers = [m for m in mig if m['rel_growth'] > 0][:10]
    fallers = [m for m in mig if m['rel_growth'] < 0][-10:]
    if risers:
        charts.bars_h([(m['topic'][:58], m['rel_growth']) for m in risers],
                      f'{zh} 份额上升最快的 10 个主题',
                      f'已扣除全校总量增长（+{A["baseline_growth"]}%）；单位 %',
                      os.path.join(d, 'up.png'), value_fmt='{:+.0f}%', top=10)
    if fallers:
        charts.bars_h([(m['topic'][:58], m['rel_growth']) for m in fallers][::-1],
                      f'{zh} 份额下降最快的 10 个主题', '同上口径，负值＝校内份额收缩',
                      os.path.join(d, 'down.png'), color=charts.ACCENT2,
                      value_fmt='{:+.0f}%', top=10)

    if mig:
        top = sorted(mig, key=lambda m: -(m['early'] + m['late']))[:10]
        charts.heat([m['topic'][:42] for m in top], ['2016–2020', '2021–2026'],
                    [[m['early'] for m in top], [m['late'] for m in top]],
                    f'{zh} 十大主题的绝对产出变化', '格子数字＝论文数（不是百分比）',
                    os.path.join(d, 'topics_heat.png'), fmt='{:.0f}', diverging=False)

    countries = [c for c in A['countries'] if c['name'] != 'Israel'][:10]
    if countries:
        charts.bars_h([(c['name'], c['count']) for c in countries],
                      f'{zh} 主要国际合著国', '合作论文计数（2016–2026）',
                      os.path.join(d, 'countries.png'), top=10)
    print(f'[{code}] figures ready', flush=True)


def main():
    only = os.environ.get('UNIS', '').strip()
    for uni in CONF['universities']:
        if only and uni['code'] not in only.split(','):
            continue
        try:
            build(uni)
        except Exception as e:
            print(f'[{uni["code"]}] figures FAILED: {type(e).__name__}: {e}', flush=True)


if __name__ == '__main__':
    main()
