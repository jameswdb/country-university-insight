# -*- coding: utf-8 -*-
"""Cross-university comparison report (10 universities, one PDF)."""
import json, io, os, sys, subprocess

from docx import Document
from docx.shared import Pt, Cm, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_BREAK
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.oxml.ns import qn
from docx.oxml import OxmlElement

if __name__ == '__main__':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, 'scripts'))
import charts

CONF = json.load(open(os.path.join(ROOT, 'config', 'universities.json'), encoding='utf-8'))
PROC = os.path.join(ROOT, 'data', 'processed')
OUT = os.path.join(ROOT, 'out')
REPORTS = os.path.join(OUT, 'reports')
FIGS = os.path.join(OUT, 'figs', '_compare')
os.makedirs(FIGS, exist_ok=True)
YEARS = [str(y) for y in range(2016, 2027)]

INK = RGBColor(0x1C, 0x21, 0x28)
MUTED = RGBColor(0x6E, 0x77, 0x81)
ACCENT = RGBColor(0x12, 0x54, 0x8F)
WHITE = RGBColor(0xFF, 0xFF, 0xFF)
ZH = 'Microsoft YaHei'
EN = 'Segoe UI'
NODE = r'D:\Tool\harness\resources\runtime\primary-runtime\dependencies\node\bin\node.exe'
CLI_A = r'D:\Tool\harness\resources\app.asar.unpacked\dsh\node_modules\@deepseek-ai\libreoffice-kit\lib\cli.js'
CLI_B = r'D:\Tool\harness\resources\runtime\primary-runtime\dependencies\node\bin\node.exe'


def set_font(run, size=10.5, bold=False, color=INK, name=ZH):
    run.font.size = Pt(size)
    run.font.bold = bold
    run.font.color.rgb = color
    run.font.name = name
    rpr = run._element.get_or_add_rPr()
    rf = rpr.find(qn('w:rFonts'))
    if rf is None:
        rf = OxmlElement('w:rFonts')
        rpr.append(rf)
    rf.set(qn('w:eastAsia'), ZH)
    rf.set(qn('w:ascii'), name)
    rf.set(qn('w:hAnsi'), name)


def para(doc, text='', size=10.5, bold=False, color=INK, align=None, space_after=6,
         space_before=0, name=ZH, line=1.42):
    p = doc.add_paragraph()
    if align is not None:
        p.alignment = align
    pf = p.paragraph_format
    pf.space_after = Pt(space_after)
    pf.space_before = Pt(space_before)
    pf.line_spacing = line
    if text:
        set_font(p.add_run(text), size, bold, color, name)
    return p


def h1(doc, num, text):
    p = doc.add_paragraph()
    p.paragraph_format.space_before = Pt(14)
    p.paragraph_format.space_after = Pt(3)
    set_font(p.add_run(f'{num}  '), 18, True, ACCENT, EN)
    set_font(p.add_run(text), 18, True, INK)
    pPr = p._p.get_or_add_pPr()
    pbdr = OxmlElement('w:pBdr')
    bottom = OxmlElement('w:bottom')
    bottom.set(qn('w:val'), 'single')
    bottom.set(qn('w:sz'), '10')
    bottom.set(qn('w:color'), '12548F')
    pbdr.append(bottom)
    pPr.append(pbdr)
    return p


def h2(doc, text):
    p = doc.add_paragraph()
    p.paragraph_format.space_before = Pt(10)
    p.paragraph_format.space_after = Pt(3)
    set_font(p.add_run(text), 13, True, INK)
    return p


def bullet(doc, text, size=10.5):
    p = doc.add_paragraph(style='List Bullet')
    p.paragraph_format.left_indent = Cm(0.5)
    p.paragraph_format.space_after = Pt(3)
    p.paragraph_format.line_spacing = 1.38
    set_font(p.add_run(text), size, False, INK)
    return p


def table(doc, headers, rows, widths=None, font_size=8.5):
    t = doc.add_table(rows=1, cols=len(headers))
    t.style = 'Table Grid'
    t.alignment = WD_TABLE_ALIGNMENT.CENTER
    t.autofit = False
    layout = OxmlElement('w:tblLayout')
    layout.set(qn('w:type'), 'fixed')
    t._tbl.tblPr.append(layout)
    for j, h in enumerate(headers):
        cell = t.rows[0].cells[j]
        shd = OxmlElement('w:shd')
        shd.set(qn('w:val'), 'clear')
        shd.set(qn('w:fill'), '12548F')
        cell._tc.get_or_add_tcPr().append(shd)
        p = cell.paragraphs[0]
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        set_font(p.add_run(str(h)), font_size, True, WHITE)
    for i, row in enumerate(rows):
        cells = t.add_row().cells
        t.rows[-1]._tr.get_or_add_trPr().append(OxmlElement('w:cantSplit'))
        for j, v in enumerate(row):
            if i % 2 == 1:
                shd = OxmlElement('w:shd')
                shd.set(qn('w:val'), 'clear')
                shd.set(qn('w:fill'), 'F5F7FA')
                cells[j]._tc.get_or_add_tcPr().append(shd)
            p = cells[j].paragraphs[0]
            p.paragraph_format.space_after = Pt(1)
            set_font(p.add_run('' if v is None else str(v)), font_size, False, INK)
    if widths:
        for j, w in enumerate(widths):
            for row in t.rows:
                row.cells[j].width = Cm(w)
    return t


def figure(doc, path, caption, width_cm=15.2):
    if not os.path.exists(path):
        return
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.space_before = Pt(6)
    p.paragraph_format.space_after = Pt(2)
    p.add_run().add_picture(path, width=Cm(width_cm))
    c = doc.add_paragraph()
    c.alignment = WD_ALIGN_PARAGRAPH.CENTER
    c.paragraph_format.space_after = Pt(8)
    set_font(c.add_run(caption), 9, False, MUTED)


def n(x):
    return f'{x:,}' if isinstance(x, int) else str(x)


def main():
    A = {}
    for uni in CONF['universities']:
        p = os.path.join(PROC, uni['code'], 'analysis.json')
        if os.path.exists(p):
            A[uni['code']] = json.load(open(p, encoding='utf-8'))
    order = sorted(A.values(), key=lambda a: -a['counts']['population'])
    print('[overview] universities:', [a['code'] for a in order])

    # ---------------- comparison figures
    charts.bars_h([(a['name_zh'], a['counts']['population']) for a in order],
                  '十校研究人口（≥6 篇论文的作者）', 'TAU 为官方名录口径，其余为 OpenAlex 署名口径',
                  os.path.join(FIGS, 'pop.png'), top=10)
    charts.bars_h([(a['name_zh'], a['counts']['works_10y']) for a in
                   sorted(order, key=lambda a: -a['counts']['works_10y'])],
                  '十校近十年可归属论文总量', '一人一篇计一次；大科学合作组会放大个人数字',
                  os.path.join(FIGS, 'works.png'), top=10)
    top5 = order[:5]
    yrs = [y for y in YEARS if y <= '2025']
    charts.line_multi({a['name_zh']: [a['inst_years'].get(y, 0) for y in yrs] for a in top5},
                      yrs, '体量最大的五校年度产出', 'OpenAlex 机构口径，2016–2025（2026 年收录不完整，已剔除）',
                      os.path.join(FIGS, 'years5.png'))
    doms = ['Physics & Astronomy', 'Chemistry', 'Materials Science', 'Engineering',
            'Computer Science', 'Mathematics', 'Life Sciences', 'Neuroscience', 'Medicine',
            'Social Sciences', 'Humanities']
    mat = []
    for a in order:
        byd = {f['domain_en']: f['n'] for f in a['faculties']}
        mat.append([byd.get(d, 0) for d in doms])
    SHORT = {'Physics & Astronomy': 'Physics', 'Chemistry': 'Chem', 'Materials Science': 'Materials',
             'Engineering': 'Eng', 'Computer Science': 'CS', 'Mathematics': 'Math',
             'Life Sciences': 'Life Sci', 'Neuroscience': 'Neuro', 'Medicine': 'Med',
             'Social Sciences': 'Social', 'Humanities': 'Human'}
    charts.heat([a['name_zh'] for a in order], [SHORT.get(d, d) for d in doms],
                mat, '大学 × 研究领域 人数矩阵', '颜色越深＝该领域人数越多', os.path.join(FIGS, 'heat.png'),
                fmt='{:.0f}', diverging=False)

    # ---------------- document
    doc = Document()
    sec = doc.sections[0]
    sec.page_width, sec.page_height = Cm(21.0), Cm(29.7)
    sec.left_margin = sec.right_margin = Cm(2.2)
    sec.top_margin = Cm(2.0)
    sec.bottom_margin = Cm(1.8)
    doc.styles['Normal'].font.name = ZH
    doc.styles['Normal'].font.size = Pt(10.5)
    fp = sec.footer.paragraphs[0]
    fp.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = fp.add_run()
    fld = OxmlElement('w:fldSimple')
    fld.set(qn('w:instr'), 'PAGE')
    r._r.addnext(fld)
    set_font(fp.add_run('  ·  Israel Insight Atlas 2026 · 十校对比  ·  '), 8, False, MUTED)

    total_pop = sum(a['counts']['population'] for a in order)
    total_a = sum(a['counts']['tier_A'] for a in order)
    total_w = sum(a['counts']['works_10y'] for a in order)

    p = doc.add_paragraph()
    p.paragraph_format.space_before = Pt(64)
    set_font(p.add_run('ISRAEL INSIGHT ATLAS'), 11, True, ACCENT, EN)
    para(doc, '以色列十校', 32, True, INK, space_before=8, space_after=2, line=1.12)
    para(doc, '教授与研究图谱', 26, True, INK, space_after=6, line=1.12)
    para(doc, f'{len(order)} 所研究型大学 ｜ 研究人口 {total_pop:,} 人 ｜ 十年论文 {total_w:,} 篇',
         13, False, MUTED, space_after=18)
    para(doc, '十校合并主库 + 十份单校报告 ｜ 数据截止 2026-11-02', 10, False, MUTED, space_after=20)
    para(doc, '名单依据 QS 2026 / THE 2026 上榜情况与研究产出体量；不含学院（college）。', 9, False, MUTED)

    # 1 summary
    doc.add_paragraph().add_run().add_break(WD_BREAK.PAGE)
    h1(doc, '01', '十校全景')
    para(doc, f'十所大学合计研究人口 {total_pop:,} 人，其中 A 层（研究型教席）{total_a:,} 人，'
              f'近十年可归属论文 {total_w:,} 篇。'
              f'体量最大的是 {order[0]["name_zh"]}（{order[0]["counts"]["population"]:,} 人），'
              f'最小的是 {order[-1]["name_zh"]}（{order[-1]["counts"]["population"]:,} 人），'
              f'相差约 {order[0]["counts"]["population"]/max(1,order[-1]["counts"]["population"]):.0f} 倍。')
    para(doc, '但“人多”不等于“产出效率高”。把每个人近十年论文数除以人数，会得到一张完全不同的排序——'
              '这正是这份对比最有价值的地方。')

    h2(doc, '十校关键指标')
    rows = []
    for a in order:
        C = a['counts']
        der = a.get('derived', {})
        rows.append([a['name_zh'], C['population'], C['tier_A'], C['works_10y'],
                     round(C['works_10y'] / max(1, C['tier_A']), 1),
                     f'{der.get("concentration", {}).get("top10pct_share", 0)*100:.0f}%',
                     der.get('pi', {}).get('median'), a['baseline_growth'],
                     a['faculties'][0]['domain_en'] if a['faculties'] else ''])
    table(doc, ['大学', '研究人口', 'A 层', '十年论文', 'A 层人均', '前10%占比', 'PI中位数',
                '五年增长 %', '第一大领域'],
          rows, widths=[3.4, 2.0, 1.5, 2.2, 1.8, 1.8, 1.7, 1.8, 3.2], font_size=7.8)
    para(doc, '', space_after=2)
    para(doc, 'TAU 为官方名录口径，其余为 OpenAlex 署名口径；直接比人数会把口径差异当成体量差异。'
              '领域按 OpenAlex 主题统一归类，因此 TAU 的“精确科学”会被拆成物理/化学/数学/计算机四类，'
              '看起来不占优势，这是归类粒度而非学科规模。', 9, False, MUTED)

    figure(doc, os.path.join(FIGS, 'pop.png'), '图 1  十校研究人口')
    figure(doc, os.path.join(FIGS, 'works.png'), '图 2  十校近十年论文总量')

    # 2 structure
    h1(doc, '02', '学科结构差异')
    para(doc, '把每所大学的研究人口按领域拆开，会看到三种截然不同的学校类型：'
              '综合型（TAU、HUJI）、工科型（Technion、HIT、Ariel）、理学型（Weizmann）。'
              '这不是排名高低，而是办学定位的差异。')
    figure(doc, os.path.join(FIGS, 'heat.png'), '图 3  大学 × 研究领域 人数矩阵', width_cm=16.0)

    h2(doc, '三种学校类型')
    for a in order:
        C = a['counts']
        f0 = a['faculties'][0] if a['faculties'] else None
        f1 = a['faculties'][1] if len(a['faculties']) > 1 else None
        if f0:
            bullet(doc, f'{a["name_zh"]}：{f0["domain_en"]} {f0["n"]:,} 人'
                        + (f'、{f1["domain_en"]} {f1["n"]:,} 人' if f1 else '')
                        + f'；十年论文 {C["works_10y"]:,} 篇，五年增长 {a["baseline_growth"]}%。')

    # 2b concentration and PI
    h2(doc, '集中度与 PI 信号')
    para(doc, '前 10% 占比＝A 层中产出最高的十分之一所贡献的论文份额；PI 中位数＝高被引论文里'
              '末位作者比例的中位数，衡量“像不像课题组负责人”。两者一起看，能区分'
              '“少数大 PI 撑起来的学校”和“分布均衡的学校”。')
    rows = []
    for a in sorted(order, key=lambda x: -(x.get('derived', {}).get('concentration', {})
                                           .get('top10pct_share') or 0)):
        der = a.get('derived', {})
        rows.append([a['name_zh'],
                     f'{der.get("concentration", {}).get("top10pct_share", 0)*100:.0f}%',
                     der.get('concentration', {}).get('top10pct_n'),
                     der.get('pi', {}).get('median'),
                     der.get('pi', {}).get('by_tier', {}).get('A', {}).get('median'),
                     len(der.get('rising_stars', []))])
    table(doc, ['大学', '前10%产出占比', '前10%人数', 'PI 中位数', 'A 层 PI 中位数', '新锐人数'], rows,
          widths=[4.2, 3.0, 2.4, 2.4, 2.8, 2.0], font_size=8)
    para(doc, '', space_after=2)
    para(doc, 'PI 中位数越高，说明该校产出越集中在负责人的课题组；新锐人数反映近年新 PI 的涌现速度。',
         9, False, MUTED)

    # 3 time
    h1(doc, '03', '十年产出的走势')
    para(doc, '把体量最大的五所大学放在同一张图里，可以看到一个共同节奏：2016–2021 年普遍上升，'
              '2022 年回落，之后恢复。差异在于恢复的速度——这往往反映了各校学科结构对疫情的暴露程度。')
    figure(doc, os.path.join(FIGS, 'years5.png'), '图 4  体量最大五校的年度产出')

    h2(doc, '谁在扩张，谁在收缩')
    rows = []
    for a in sorted(order, key=lambda x: -(x['baseline_growth'] or 0)):
        rows.append([a['name_zh'], f'{a["baseline_growth"]}%' if a['baseline_growth'] is not None else '—',
                     a['topic_migration'][0]['topic'] if a['topic_migration'] else '',
                     f'{a["topic_migration"][0]["rel_growth"]:+.0f}%' if a['topic_migration'] else ''])
    table(doc, ['大学', '五年增长', '份额上升最快的主题', '相对增长'], rows,
          widths=[4.2, 2.4, 8.6, 2.4], font_size=8)
    para(doc, '', space_after=2)
    para(doc, '各校的“上升主题”高度集中在 AI/计算、肿瘤免疫、量子与低维材料——'
              '说明以色列高校的方向调整是同步的，差异更多在速度而非方向。', 10)

    # 4 how to use
    doc.add_paragraph().add_run().add_break(WD_BREAK.PAGE)
    h1(doc, '04', '怎么用这套材料')
    bullet(doc, '找合作者：合并主库「03 A层重点」按领域筛选，再按“近三年论文”降序，优先选仍在高强度产出的 PI。')
    bullet(doc, '做校际对标：合并主库「04 领域矩阵」看学科结构，「01 十校总览」看体量与增长，'
                '两者结合才能区分“大而全”和“小而强”。')
    bullet(doc, '看单校细节：每所大学有独立 PDF（out/reports/<CODE>_教授研究图谱.pdf），含该校主题迁移与人员榜单。')
    bullet(doc, '查人：主库含 OpenAlex 个人主页链接，可直接跳转核对其论文与主题。')

    h1(doc, '05', '局限')
    bullet(doc, '口径不一致：只有 TAU 有官方名录；其余九校的职称与院系是推断值，不能当人事数据用。')
    bullet(doc, '人数不可跨校直接比较：官方名录口径包含不发表论文的教师，OpenAlex 口径只含发表者。')
    bullet(doc, '大科学合作组放大：ATLAS/CMS 论文作者数千，粒子物理学者的人均论文数会被显著推高。')
    bullet(doc, '2026 年不完整：OpenAlex 收录滞后 3–9 个月，年度结论以 2025 年及以前为准。')

    out_docx = os.path.join(REPORTS, '00_以色列十校_对比总览.docx')
    doc.save(out_docx)
    cli = CLI_A if os.path.exists(CLI_A) else CLI_B
    pdf = out_docx[:-5] + '.pdf'
    if os.path.exists(pdf):
        os.remove(pdf)
    r = subprocess.run([NODE, cli, 'convert', '--input', out_docx, '--output', pdf],
                       capture_output=True, timeout=300)
    print('[overview]', 'PDF ok' if os.path.exists(pdf) else 'PDF FAILED',
          os.path.getsize(pdf) // 1024 if os.path.exists(pdf) else '',
          (r.stderr or b'')[-300:].decode('utf-8', 'replace'))


if __name__ == '__main__':
    main()
