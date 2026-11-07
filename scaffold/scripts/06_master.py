# -*- coding: utf-8 -*-
"""Combined master workbook: all ten universities in one filterable database."""
import json, io, os, sys, collections
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter
from openpyxl.chart import BarChart, Reference

if __name__ == '__main__':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONF = json.load(open(os.path.join(ROOT, 'config', 'universities.json'), encoding='utf-8'))
PROC = os.path.join(ROOT, 'data', 'processed')
OUT = os.path.join(ROOT, 'out')

INK = '1C2128'
ACCENT = '12548F'
STRIPE = 'F5F7FA'
GRIDC = 'D9DEE5'
HFONT = Font(name='Microsoft YaHei', size=10, bold=True, color='FFFFFF')
BFONT = Font(name='Microsoft YaHei', size=10)
TITLE = Font(name='Microsoft YaHei', size=16, bold=True, color=INK)
SUB = Font(name='Microsoft YaHei', size=10, color='6E7781')
HFILL = PatternFill('solid', fgColor=ACCENT)
STRIPEF = PatternFill('solid', fgColor=STRIPE)
THIN = Side(style='thin', color=GRIDC)
BORDER = Border(left=THIN, right=THIN, top=THIN, bottom=THIN)
PROV_ZH = {'official': '官方名录', 'openalex': 'OpenAlex 推断'}


def sheet_title(ws, title, subtitle, ncols):
    ws.merge_cells(start_row=1, start_column=1, end_row=1, end_column=max(4, ncols))
    c = ws.cell(row=1, column=1, value=title)
    c.font = TITLE
    ws.row_dimensions[1].height = 26
    ws.merge_cells(start_row=2, start_column=1, end_row=2, end_column=max(4, ncols))
    c2 = ws.cell(row=2, column=1, value=subtitle)
    c2.font = SUB
    c2.alignment = Alignment(wrap_text=True, vertical='top')
    ws.row_dimensions[2].height = 30


def write_table(ws, start_row, headers, rows, widths=None, num_formats=None, free=True,
                wrap_cols=()):
    for j, h in enumerate(headers, start=1):
        c = ws.cell(row=start_row, column=j, value=h)
        c.font = HFONT
        c.fill = HFILL
        c.alignment = Alignment(horizontal='center', vertical='center', wrap_text=True)
        c.border = BORDER
    ws.row_dimensions[start_row].height = 32
    for i, row in enumerate(rows):
        for j, v in enumerate(row, start=1):
            c = ws.cell(row=start_row + 1 + i, column=j, value=v)
            c.font = BFONT
            c.border = BORDER
            c.alignment = Alignment(vertical='top', wrap_text=(j in wrap_cols))
            if i % 2 == 1:
                c.fill = STRIPEF
            if num_formats and j in num_formats:
                c.number_format = num_formats[j]
    if free and rows:
        ws.freeze_panes = ws.cell(row=start_row + 1, column=3)
        ws.auto_filter.ref = (f'A{start_row}:{get_column_letter(len(headers))}'
                              f'{start_row + len(rows)}')
    if widths:
        for j, w in enumerate(widths, start=1):
            ws.column_dimensions[get_column_letter(j)].width = w


def main():
    analyses, rows_all = {}, []
    for uni in CONF['universities']:
        code = uni['code']
        ap = os.path.join(PROC, code, 'analysis.json')
        fp = os.path.join(PROC, code, 'faculty.json')
        if not (os.path.exists(ap) and os.path.exists(fp)):
            print(f'[{code}] missing analysis, skipped')
            continue
        A = json.load(open(ap, encoding='utf-8'))
        analyses[code] = A
        for r in json.load(open(fp, encoding='utf-8')):
            rows_all.append({
                'univ': code, 'univ_en': uni['name_en'], 'univ_zh': uni['name_zh'],
                'prov': A['provenance'],
                'name': r.get('name') or '', 'name_he': r.get('name_he') or '',
                'id': r.get('id') or '', 'url': r.get('url') or '',
                'tier': r.get('tier') or '', 'rank_zh': r.get('rank_zh') or '',
                'domain_en': r.get('domain_en') or '', 'domain_zh': r.get('domain_zh') or '',
                'w10': r.get('works_10y'), 'w_e': r.get('works_2016_2020'),
                'w_l': r.get('works_2021_2026'), 'w_r': r.get('works_2024_2026'),
                'w_total': r.get('works_total'), 'span': r.get('span'),
                'h': r.get('h'), 'cited': r.get('cited'),
                'activity': r.get('activity') or '',
                'topics': '; '.join((r.get('top_topics') or [])[:5]),
                'orcid': r.get('orcid') or '',
                'last_share': r.get('last_share'),
                'rising': '是' if r.get('rising') else '',
                'cpw': r.get('cite_per_work'),
                'orcid_current': r.get('orcid_current') or '',
                'orcid_history': r.get('orcid_history') or '',
                'orcid_degrees': r.get('orcid_degrees') or '',
                'orcid_role': r.get('orcid_role_class') or '',
                's2_id': r.get('s2_id') or '',
                's2_papers': r.get('s2_papers'),
                's2_cites': r.get('s2_citations'),
                's2_h': r.get('s2_hindex'),
                's2_infl': r.get('s2_influential'),
                's2_infl_pp': r.get('s2_infl_per_paper'),
                's2_top': r.get('s2_top_title') or '',
                's2_tldr': r.get('s2_top_tldr') or '',
            })
    rows_all.sort(key=lambda x: (x['univ'], x['tier'], -(x['w10'] or 0)))
    print(f'[master] rows={len(rows_all)} universities={len(analyses)}')

    wb = Workbook()
    ws = wb.active
    ws.title = '00 说明'
    ws.sheet_view.showGridLines = False
    sheet_title(ws, '以色列十校 教授与研究图谱 · Israel Insight Atlas',
                f'数据截止 2026-11-02 ｜ 十所研究型大学 ｜ 合并主库 {len(rows_all):,} 条记录', 8)
    total_pop = sum(A['counts']['population'] for A in analyses.values())
    total_a = sum(A['counts']['tier_A'] for A in analyses.values())
    total_w = sum(A['counts']['works_10y'] for A in analyses.values())
    blocks = [
        ('一、这份表是什么',
         f'把以色列十所主要研究型大学的教授与研究人员放进同一个可筛选数据库：'
         f'研究人口合计 {total_pop:,} 人，其中 A 层（研究型教席）{total_a:,} 人，十年可归属论文 {total_w:,} 篇。'
         '每所大学另有一份独立 PDF 报告。'),
        ('二、十校名单与口径',
         '名单依据 QS 2026 / THE 2026 上榜情况与研究产出体量：特拉维夫大学、希伯来大学、以色列理工学院、'
         '魏茨曼科学研究所、本-古里安大学、巴伊兰大学、海法大学、赖希曼大学、阿里尔大学、霍隆理工学院。'
         '不含学院（college）。'),
        ('三、两种人员口径（必读）',
         'TAU 使用官方人员名录（含希伯来职称），其余九校无公开统一名录，采用 OpenAlex 署名作者口径：'
         '研究人口＝last-known 机构为该校且 ≥6 篇论文的作者；A/B/C 分层由发表跨度与产出推断，'
         '领域由 OpenAlex 主题推断。因此“人数”在两套口径间不可直接相加或比较，趋势可以。'),
        ('四、分层规则',
         'A 层：发表跨度 ≥12 年且 ≥12 篇；B 层：跨度 ≥9 年且 ≥8 篇；C 层：其余（多为博士生、博士后、访问学者）。'
         'TAU 的 A 层沿用官方职称筛选结果。'),
        ('五、字段字典',
         'works_10y=近十年论文；works_2016_2020 / works_2021_2026=前后五年；works_2024_2026=近三年；'
         'span=发表跨度（年）；tier=A/B/C；domain=研究领域（主题推断）；prov=人员口径。'),
        ('六、已知局限',
         '① 无官方职称的九校，A 层含资深研究员与临床教授，也漏掉新入职者；'
         '② 大科学合作组（ATLAS/CMS）按篇计数会放大个人数字；'
         '③ 2026 年收录不完整；④ 同名同姓仍有残余误配。'),
    ]
    r = 4
    ws.column_dimensions['A'].width = 26
    for col in 'BCDEFGH':
        ws.column_dimensions[col].width = 19
    for head, body in blocks:
        c = ws.cell(row=r, column=1, value=head)
        c.font = Font(name='Microsoft YaHei', size=11, bold=True, color=ACCENT)
        c.alignment = Alignment(vertical='top')
        b = ws.cell(row=r, column=2, value=body)
        b.font = BFONT
        b.alignment = Alignment(wrap_text=True, vertical='top')
        ws.merge_cells(start_row=r, start_column=2, end_row=r, end_column=8)
        ws.row_dimensions[r].height = max(30, 15 * (len(body) // 54 + 1))
        r += 1

    # ---------------- 01 overview
    ws = wb.create_sheet('01 十校总览')
    ws.sheet_view.showGridLines = False
    sheet_title(ws, '十校总览', '研究人口 / A 层 / 论文 / 增长 / 第一大领域', 12)
    rows = []
    for code, A in analyses.items():
        C = A['counts']
        top = A['faculties'][0]['domain_en'] if A['faculties'] else ''
        der = A.get('derived', {})
        rows.append([code, A['name_zh'], A['name_en'], A['city'], PROV_ZH.get(A['provenance'], ''),
                     C['population'], C['tier_A'], C['works_10y'], C['works_recent'],
                     A['baseline_growth'], top,
                     A['topics'][0]['name'] if A['topics'] else '',
                     round(C['works_10y'] / max(1, C['tier_A']), 1),
                     der.get('concentration', {}).get('top10pct_share'),
                     der.get('pi', {}).get('median')])
    hdr = 4
    write_table(ws, hdr, ['代码', '大学（中）', 'University', '城市', '人员口径', '研究人口', 'A 层',
                          '十年论文', '近三年', '五年增长 %', '第一大领域', '第一大主题',
                          'A 层人均', '前10%占比', 'PI中位数'], rows,
                widths=[8, 18, 34, 12, 12, 10, 8, 11, 9, 11, 22, 40, 10, 11, 11],
                num_formats={6: '#,##0', 7: '#,##0', 8: '#,##0', 9: '#,##0', 10: '0.0',
                             13: '0.0', 14: '0%', 15: '0.00'},
                wrap_cols=(12,))
    ch = BarChart()
    ch.type = 'bar'
    ch.title = '十校研究人口'
    ch.height, ch.width = 9, 15
    ch.add_data(Reference(ws, min_col=6, min_row=hdr, max_row=hdr + len(rows)), titles_from_data=True)
    ch.set_categories(Reference(ws, min_col=2, min_row=hdr + 1, max_row=hdr + len(rows)))
    ch.legend = None
    ws.add_chart(ch, f'A{hdr + len(rows) + 3}')

    # ---------------- 02 master
    ws = wb.create_sheet('02 合并主库')
    headers = ['大学', '大学（中）', '姓名', '希伯来名', 'OpenAlex ID', '个人主页', '口径',
               '层级', '职称(官方)', '研究领域 EN', '领域(中)', '近十年论文', '2016-2020',
               '2021-2026', '2024-2026', '累计论文', '发表跨度', 'h-index', '累计被引',
               '活跃度', '末位作者比例', '新锐', '篇均被引', '现职类型（ORCID）', '现职（ORCID）',
               '任职经历（ORCID）', '学历（ORCID）',
               'S2 h-index', 'S2 论文数', 'S2 被引', '影响力引用', '影响力引用/篇',
               'S2 代表作', '代表作一句话（TLDR）', '主要研究主题', 'ORCID']
    rows = []
    for x in rows_all:
        rows.append([x['univ'], x['univ_zh'], x['name'], x['name_he'], x['id'], x['url'],
                     PROV_ZH.get(x['prov'], ''), x['tier'], x['rank_zh'], x['domain_en'],
                     x['domain_zh'], x['w10'], x['w_e'], x['w_l'], x['w_r'], x['w_total'],
                     x['span'], x['h'], x['cited'], x['activity'], x['last_share'], x['rising'],
                     x['cpw'], x['orcid_role'], x['orcid_current'], x['orcid_history'],
                     x['orcid_degrees'],
                     x['s2_h'], x['s2_papers'], x['s2_cites'], x['s2_infl'], x['s2_infl_pp'],
                     x['s2_top'], x['s2_tldr'], x['topics'], x['orcid']])
    sheet_title(ws, f'合并主库 · {len(rows):,} 条记录',
                '按大学 → 层级 → 近十年论文排序 ｜ 可筛选 ｜ 口径列区分官方名录与 OpenAlex 推断', 22)
    write_table(ws, 4, headers, rows,
                widths=[8, 16, 24, 16, 14, 32, 12, 6, 10, 20, 11, 10, 10, 10, 10, 10, 9, 8, 10, 9,
                        11, 6, 9, 10, 34, 46, 30, 8, 9, 9, 9, 11, 46, 52, 52, 20],
                num_formats={12: '#,##0', 13: '#,##0', 14: '#,##0', 15: '#,##0', 16: '#,##0',
                             17: '#,##0', 19: '#,##0', 21: '0.00', 23: '0.0',
                             24: '#,##0', 25: '#,##0', 26: '#,##0', 27: '#,##0', 28: '0.00'},
                wrap_cols=(25, 26, 27, 29, 30, 31))

    # ---------------- 03 A tier
    ws = wb.create_sheet('03 A层重点')
    ws.sheet_view.showGridLines = False
    Arows = [x for x in rows_all if x['tier'] == 'A']
    sheet_title(ws, f'A 层 · {len(Arows):,} 位研究型教席（含官方职称的 TAU 记录）',
                '用于找合作者、招生导师与对标学者 ｜ 按大学 → 近十年论文排序', 12)
    rows = []
    for i, x in enumerate(Arows, 1):
        rows.append([i, x['univ'], x['name'], x['rank_zh'], x['domain_en'], x['domain_zh'],
                     x['w10'], x['w_r'], x['span'], x['last_share'],
                     ('是' if x['rising'] else ''), x['topics'][:120], x['url']])
    write_table(ws, 4, ['#', '大学', '姓名', '职称/层级', '领域 EN', '领域(中)', '近十年论文',
                        '近三年', '跨度', '末位作者比例', '新锐', '主要研究主题', '个人主页'], rows,
                widths=[6, 8, 24, 12, 20, 11, 11, 9, 8, 11, 6, 56, 34],
                num_formats={7: '#,##0', 8: '#,##0', 9: '#,##0', 10: '0.00'}, wrap_cols=(12,))

    # ---------------- 04 domain matrix
    ws = wb.create_sheet('04 领域矩阵')
    ws.sheet_view.showGridLines = False
    sheet_title(ws, '大学 × 研究领域 人数矩阵', '用于看各校的学科结构差异；行＝大学，列＝领域', 14)
    domains = ['Physics & Astronomy', 'Chemistry', 'Materials Science', 'Engineering',
               'Computer Science', 'Mathematics', 'Life Sciences', 'Neuroscience', 'Medicine',
               'Environment & Energy', 'Social Sciences', 'Management',
               'Architecture & Planning', 'Humanities', 'Law']
    rows = []
    for code, A in analyses.items():
        bydom = {f['domain_en']: f for f in A['faculties']}
        rows.append([code, A['name_zh']] + [bydom.get(d, {}).get('n', 0) for d in domains])
    write_table(ws, 4, ['代码', '大学（中）'] + [d.replace(' & ', ' &\n') for d in domains], rows,
                widths=[8, 16] + [9] * len(domains),
                num_formats={i: '#,##0' for i in range(3, 3 + len(domains))})

    # ---------------- 05 topics
    ws = wb.create_sheet('05 主题迁移')
    ws.sheet_view.showGridLines = False
    sheet_title(ws, '各校主题份额变化', '相对增长已扣除各校总量增长；只列可比主题（两窗口各 ≥15 篇）', 7)
    rows = []
    for code, A in analyses.items():
        for m in A['topic_migration'][:8]:
            rows.append([code, A['name_zh'], m['topic'], m['early'], m['late'], m['rel_growth'], '上升'])
        for m in A['topic_migration'][-8:]:
            rows.append([code, A['name_zh'], m['topic'], m['early'], m['late'], m['rel_growth'], '下降'])
    write_table(ws, 4, ['代码', '大学', '主题', '2016-2020', '2021-2026', '相对增长 %', '方向'], rows,
                widths=[8, 16, 60, 12, 12, 12, 8],
                num_formats={4: '#,##0', 5: '#,##0', 6: '0.0'}, wrap_cols=(3,))

    # ---------------- 07 specialisation
    ws = wb.create_sheet('07 专门化指数')
    ws.sheet_view.showGridLines = False
    sheet_title(ws, '大学 × 研究领域 专门化指数',
                '本校该领域产出份额 ÷ 十校平均份额；>1.3 为特色强项，<0.7 为相对薄弱', 14)
    rows = []
    for code, A in analyses.items():
        idx = {sp['domain_en']: sp['index'] for sp in A.get('derived', {}).get('specialisation', [])}
        rows.append([code, A['name_zh']] + [idx.get(d) for d in domains])
    write_table(ws, 4, ['代码', '大学（中）'] + [d.replace(' & ', ' &\n') for d in domains], rows,
                widths=[8, 16] + [9] * len(domains),
                num_formats={i: '0.00' for i in range(3, 3 + len(domains))})

    # ---------------- 06 sources
    ws = wb.create_sheet('06 数据源')
    ws.sheet_view.showGridLines = False
    sheet_title(ws, '数据源与脚本', '全部公开数据 ｜ 脚本在 insight/scripts/', 5)
    src = [['OpenAlex authors', 'api.openalex.org/authors', '作者档案、主题、逐年产出', '01_download.py'],
           ['OpenAlex works group_by', 'api.openalex.org/works', '年度/主题/国别/类型/OA', '02_trends.py'],
           ['TAU 官方名录', 'www.tau.ac.il/tau/index', '13,808 条，含希伯来职称', '（TAU 项目）'],
           ['Technion 物理系名单', 'phys.technion.ac.il', '38 位，用于校验 A 层', '（TECH 项目）'],
           ['ROR', 'ror.org', '机构标识', '—']]
    write_table(ws, 4, ['数据源', '入口', '内容', '脚本'], src,
                widths=[26, 34, 44, 26], free=False, wrap_cols=(3, 4))

    path = os.path.join(OUT, 'Israel十校_教授研究主库.xlsx')
    wb.save(path)
    print('[master] saved', path, os.path.getsize(path) // 1024, 'KB')
    print('  A tier rows:', len(Arows))


if __name__ == '__main__':
    main()
