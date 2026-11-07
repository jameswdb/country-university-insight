# -*- coding: utf-8 -*-
"""Per-university report, TAU/Technion depth: 12-14 pages with a validation chapter.

Sections
  01 执行摘要          4 data-driven findings (scale, concentration, specialisation, PI)
  02 方法与校验        provenance, tier rules, PI signal, validation limits
  03 全校产出与结构    yearly output, types, open access, countries
  04 学科结构          domains, specialisation index vs the ten-university average
  05 主题迁移          relative + absolute topic shift
  06 人                top by 10y, top by recent, rising stars, PI leaders
  07 十校中的位置      where this university sits among the ten
  08 局限
  A  附录               sources, field dictionary
"""
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
CONF = json.load(open(os.path.join(ROOT, 'config', 'universities.json'), encoding='utf-8'))
PROC = os.path.join(ROOT, 'data', 'processed')
FIGS = os.path.join(ROOT, 'out', 'figs')
REPORTS = os.path.join(ROOT, 'out', 'reports')

INK = RGBColor(0x1C, 0x21, 0x28)
MUTED = RGBColor(0x6E, 0x77, 0x81)
ACCENT = RGBColor(0x12, 0x54, 0x8F)
WHITE = RGBColor(0xFF, 0xFF, 0xFF)
ZH = 'Microsoft YaHei'
EN = 'Segoe UI'
NODE = r'D:\Tool\harness\resources\runtime\primary-runtime\dependencies\node\bin\node.exe'

# What was actually probed while checking for a bulk-downloadable official roster.
# Kept in the report so the "inferred" label is auditable rather than assumed.
ROSTER_CHECK = {
    'TAU': [('TAU 官方通讯录（אלפון）', '✅ 可批量获取 13,808 条，含希伯来职称与院系'),
            ('结论', '使用官方职称；论文指标通过姓名匹配挂接')],
    'TECH': [('my.technion.ac.il 电话簿', '🔒 需校内登录'),
             ('cris.technion.ac.il/en/persons', '🔒 403，Cloudflare 拦截'),
             ('Pure API /ws/api', '🔑 需机构 API key'),
             ('18 个院系子站', '⚠️ 分散，多数只有英文姓名、无职称字段'),
             ('结论', '无可用官方名录，改用 OpenAlex 署名口径')],
    'HUJI': [('huji.ac.il 人员检索', '❌ 未找到可批量获取的名录'),
             ('info.huji.ac.il', '⚠️ 招生门户，非人员目录'),
             ('结论', 'OpenAlex 署名口径')],
    'WIS': [('weizmann.ac.il/pages', '⚠️ 通用页面，无人员名录'),
            ('各院系站点', '⚠️ 仅部分系所有英文人员页，无统一职称字段'),
            ('结论', 'OpenAlex 署名口径')],
    'BGU': [('in.bgu.ac.il', '❌ 无可解析的统一名录'),
            ('CRIS / Pure', '❌ 无公开人员接口'),
            ('结论', 'OpenAlex 署名口径')],
    'BIU': [('biu.ac.il/en/staff', '⚠️ 返回 Radware 验证码，无法批量'),
            ('结论', 'OpenAlex 署名口径')],
    'HAIFA': [('haifa.ac.il', '⚠️ 主页可访问，无统一人员名录'),
              ('结论', 'OpenAlex 署名口径')],
    'REICH': [('runi.ac.il/en/faculty', '❌ 404'),
              ('结论', 'OpenAlex 署名口径')],
    'ARIEL': [('ariel.ac.il', '⚠️ 反爬（HTTP 247）'),
              ('结论', 'OpenAlex 署名口径')],
    'HIT': [('hit.ac.il/en/faculty', '❌ 404'),
            ('结论', 'OpenAlex 署名口径')],
    'default': [('官网与院系站点', '❌ 未找到可批量获取的名录'),
                ('结论', 'OpenAlex 署名口径')],
}

CLI = r'D:\Tool\harness\resources\app.asar.unpacked\dsh\node_modules\@deepseek-ai\libreoffice-kit\lib\cli.js'


# ------------------------------------------------------------------ helpers
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
         space_before=0, name=ZH, line=1.4):
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
    p.paragraph_format.space_before = Pt(13)
    p.paragraph_format.space_after = Pt(3)
    p.paragraph_format.keep_with_next = True
    set_font(p.add_run(f'{num}  '), 17.5, True, ACCENT, EN)
    set_font(p.add_run(text), 17.5, True, INK)
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
    p.paragraph_format.space_before = Pt(9)
    p.paragraph_format.space_after = Pt(3)
    p.paragraph_format.keep_with_next = True
    set_font(p.add_run(text), 12.5, True, INK)
    return p


def bullet(doc, text, size=10.2):
    p = doc.add_paragraph(style='List Bullet')
    p.paragraph_format.left_indent = Cm(0.5)
    p.paragraph_format.space_after = Pt(3)
    p.paragraph_format.line_spacing = 1.36
    set_font(p.add_run(text), size, False, INK)
    return p


def quote_box(doc, text, color='EAF1F8'):
    t = doc.add_table(rows=1, cols=1)
    t.alignment = WD_TABLE_ALIGNMENT.CENTER
    cell = t.cell(0, 0)
    cell.width = Cm(16.4)
    shd = OxmlElement('w:shd')
    shd.set(qn('w:val'), 'clear')
    shd.set(qn('w:fill'), color)
    cell._tc.get_or_add_tcPr().append(shd)
    p = cell.paragraphs[0]
    p.paragraph_format.space_before = Pt(6)
    p.paragraph_format.space_after = Pt(6)
    p.paragraph_format.line_spacing = 1.36
    set_font(p.add_run(text), 10.2, False, INK)


def figure(doc, path, caption, width_cm=12.4):
    if not os.path.exists(path):
        return
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.space_before = Pt(5)
    p.paragraph_format.space_after = Pt(1)
    p.add_run().add_picture(path, width=Cm(width_cm))
    c = doc.add_paragraph()
    c.alignment = WD_ALIGN_PARAGRAPH.CENTER
    c.paragraph_format.space_after = Pt(7)
    set_font(c.add_run(caption), 8.8, False, MUTED)


def table(doc, headers, rows, widths=None, font_size=8.3):
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
        # LibreOffice honours the table grid, not just cell widths, so write both.
        for j, w in enumerate(widths):
            for row in t.rows:
                row.cells[j].width = Cm(w)
        grid = t._tbl.find(qn('w:tblGrid'))
        if grid is not None:
            for j, gc in enumerate(grid.findall(qn('w:gridCol'))):
                if j < len(widths):
                    gc.set(qn('w:w'), str(int(Cm(widths[j]).twips)))
        tblW = t._tbl.tblPr.find(qn('w:tblW'))
        if tblW is None:
            tblW = OxmlElement('w:tblW')
            t._tbl.tblPr.append(tblW)
        tblW.set(qn('w:type'), 'dxa')
        tblW.set(qn('w:w'), str(int(Cm(sum(widths)).twips)))
    return t


def page_break(doc):
    doc.add_paragraph().add_run().add_break(WD_BREAK.PAGE)


def n(x):
    return f'{x:,}' if isinstance(x, int) else str(x)


# ------------------------------------------------------------------ build
def build(uni):
    code = uni['code']
    A = json.load(open(os.path.join(PROC, code, 'analysis.json'), encoding='utf-8'))
    F = json.load(open(os.path.join(PROC, code, 'faculty.json'), encoding='utf-8'))
    R = json.load(open(os.path.join(PROC, '_ten_ranking.json'), encoding='utf-8'))
    D = A.get('derived', {})
    C = A['counts']
    figd = os.path.join(FIGS, code)
    zh, en = uni['name_zh'], uni['name_en']
    years = A['inst_years']
    yc = {k: v for k, v in years.items() if k <= '2025'}
    y16, y25 = years.get('2016', 0), years.get('2025', 0)
    peak_y = max(yc, key=lambda k: yc[k]) if yc else '—'
    peak_v = yc.get(peak_y, 0)
    growth = A['baseline_growth']
    facs = A['faculties']
    mig = A['topic_migration']
    risers = [m for m in mig if m['rel_growth'] > 0][:5]
    fallers = [m for m in mig if m['rel_growth'] < 0][-5:][::-1]
    conc = D.get('concentration', {})
    pi = D.get('pi', {})
    spec = [s for s in D.get('specialisation', []) if s.get('index')]
    stars = D.get('rising_stars', [])
    rank = {r['code']: r for r in R}

    doc = Document()
    sec = doc.sections[0]
    sec.page_width, sec.page_height = Cm(21.0), Cm(29.7)
    sec.left_margin = sec.right_margin = Cm(2.3)
    sec.top_margin = Cm(2.0)
    sec.bottom_margin = Cm(1.75)
    doc.styles['Normal'].font.name = ZH
    doc.styles['Normal'].font.size = Pt(10.5)
    fp = sec.footer.paragraphs[0]
    fp.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = fp.add_run()
    fld = OxmlElement('w:fldSimple')
    fld.set(qn('w:instr'), 'PAGE')
    r._r.addnext(fld)
    set_font(fp.add_run(f'  ·  Israel Insight Atlas 2026 · {code}  ·  '), 8, False, MUTED)

    # ---------------- cover
    p = doc.add_paragraph()
    p.paragraph_format.space_before = Pt(58)
    set_font(p.add_run(en.upper()), 10.5, True, ACCENT, EN)
    para(doc, zh, 31, True, INK, space_before=8, space_after=2, line=1.1)
    para(doc, '教授与研究图谱', 25, True, INK, space_after=4, line=1.1)
    para(doc, f'{A["city"]} ｜ 研究人口 {C["population"]:,} 人 ｜ 十年署名 {C["works_10y"]:,} 次',
         12.5, False, MUTED, space_after=2)
    para(doc, 'Faculty, research fields and a decade of change (2016–2026)', 9.5, False, MUTED,
         space_after=20, name=EN)

    t = doc.add_table(rows=1, cols=4)
    t.alignment = WD_TABLE_ALIGNMENT.CENTER
    kpis = [(f'{C["population"]:,}', '研究人口'), (f'{C["tier_A"]:,}', 'A 层教席'),
            (f'{conc.get("top10pct_share", 0)*100:.0f}%', '前 10% 产出占比'),
            (f'{growth}%', '五年增长')]
    for j, (v, k) in enumerate(kpis):
        cell = t.cell(0, j)
        cell.width = Cm(4.1)
        pp = cell.paragraphs[0]
        pp.alignment = WD_ALIGN_PARAGRAPH.CENTER
        set_font(pp.add_run(v), 21, True, ACCENT, EN)
        p2 = cell.add_paragraph()
        p2.alignment = WD_ALIGN_PARAGRAPH.CENTER
        set_font(p2.add_run(k), 8.8, False, MUTED)

    para(doc, '', space_after=22)
    quote_box(doc, ('人员口径：' + ('该校有公开的官方人员名录，职称与院系取自官方数据。'
                                 if A['provenance'] == 'official' else
                                 '该校无公开的统一人员名录，人员基底为 OpenAlex 署名作者，'
                                 'A/B/C 分层、领域归属与 PI 信号均由发表行为推断。'))
                   + '所有指标可回溯到 OpenAlex 作者档案；推断方法与误差写在第 2 章。')
    para(doc, '', space_after=14)
    para(doc, 'Israel Insight Atlas ｜ 以色列十校教授研究图谱 ｜ 数据截止 2026-11-02',
         8.8, False, MUTED)

    # ---------------- 01 summary
    page_break(doc)
    h1(doc, '01', '执行摘要')
    para(doc, f'{zh} 2016 年产出 {n(y16)} 篇，{peak_y} 年达 {n(peak_v)} 篇峰值，2025 年为 {n(y25)} 篇'
              f'（2026 年收录不完整，未纳入比较）。研究人口 {C["population"]:,} 人，其中 A 层 '
              f'{C["tier_A"]:,} 人；机构口径十年论文 {n(C["institution_works_10y"])} 篇，'
              f'研究人口在同一窗口的署名次数 {n(C["works_10y"])} 次（一篇多作者重复计，故大于论文数）。')

    h2(doc, '四个判断')
    bullet(doc, f'规模与集中度：A 层人均十年署名 {conc.get("a_tier_output", 0) / max(1, C["tier_A"]):.1f} 次，'
                f'前 10%（{conc.get("top10pct_n", 0)} 人）贡献了 A 层总产出的 '
                f'{conc.get("top10pct_share", 0) * 100:.0f}%。'
                + ('产出高度集中在少数 PI 身上。' if conc.get('top10pct_share', 0) > 0.4
                   else '产出分布相对分散，团队规模较均衡。'))
    if spec:
        bullet(doc, f'学科专门化：相对十校平均，最强的是 {spec[0]["domain_en"]}'
                    f'（占比 {spec[0]["share"]*100:.0f}%，为十校均值的 {spec[0]["index"]:.1f} 倍）'
                    + (f'，其次是 {spec[1]["domain_en"]}（{spec[1]["index"]:.1f} 倍）'
                       if len(spec) > 1 else '') + '。')
    if pi.get('median') is not None:
        a_m = pi.get('by_tier', {}).get('A', {}).get('median')
        c_m = pi.get('by_tier', {}).get('C', {}).get('median')
        bullet(doc, f'PI 信号：抽样 {pi.get("n_A", 0)} 位 A 层与 '
                    f'{pi.get("by_tier", {}).get("C", {}).get("n", 0)} 位 C 层研究者的高被引论文，'
                    f'A 层末位作者比例中位数 {a_m:.2f}'
                    + (f'，C 层仅 {c_m:.2f}' if c_m is not None else '')
                    + '——分层规则确实把课题组负责人和早期研究人员区分开了。')
    bullet(doc, f'新锐：{len(stars)} 位 A 层研究者的近三年产出速度达到 2016–2020 年的 1.8 倍以上'
                + (f'，其中 {stars[0]["name"]}（近三年 {stars[0]["recent"]} 篇）最快。' if stars else '。'))

    h2(doc, '各领域结构')
    rows = [[f['domain_en'], f['n'], f['A'], f['works'], f['per_capita'],
             f'{f["growth_pct"]:+.0f}%' if f['growth_pct'] is not None else '—'] for f in facs[:8]]
    table(doc, ['研究领域', '人数', 'A 层', '署名次数', '人均', '五年变化'], rows,
          widths=[5.0, 1.5, 1.4, 2.1, 1.4, 1.9])
    para(doc, '', space_after=2)
    para(doc, '人数与论文量只反映体量；跨领域比较人均要谨慎，学科出版密度差异远大于研究强度差异。',
         8.8, False, MUTED)

    # ---------------- 02 method & validation
    h1(doc, '02', '方法与校验')
    h2(doc, '2.1 人员口径')
    if A['provenance'] == 'official':
        para(doc, f'{zh} 有公开的官方人员名录（含职称、院系），论文指标通过姓名匹配挂到 OpenAlex 档案，'
                  f'匹配结果分级标注；最终研究人口 {C["population"]:,} 人。')
    else:
        para(doc, f'{zh} 没有可公开访问的统一人员名录（官网电话簿需校内登录、CRIS 被 Cloudflare 拦截、'
                  f'Pure API 需机构密钥），因此以 OpenAlex 中 last-known 机构为该校、且 ≥6 篇论文的作者为'
                  f'研究人口，共 {C["population"]:,} 人。职称字段不存在于数据源。')
    h2(doc, '2.2 官方名录可得性核查')
    para(doc, '做这十份报告前，逐校核查过是否存在可批量获取的官方人员名录。结论如下——'
              '这也是为什么只有 TAU 用官方职称、其余九校用推断口径。', 9.8)
    checks = ROSTER_CHECK.get(code, ROSTER_CHECK['default'])
    table(doc, ['来源', '结果'], [[a, b] for a, b in checks],
          widths=[6.6, 9.8], font_size=8)

    h2(doc, '2.3 分层与 PI 信号')
    rows = [['A 层（研究型教席，推断）', n(C['tier_A']), '发表跨度 ≥12 年且 ≥12 篇'],
            ['B 层（可能为教席）', n(C['tier_B']), '跨度 ≥9 年且 ≥8 篇'],
            ['C 层（其他研究人员）', n(C['tier_C']), '其余，多为博士生、博士后、访问学者']]
    table(doc, ['层级', '人数', '规则'], rows, widths=[4.8, 2.0, 9.6])
    para(doc, '', space_after=2)
    para(doc, 'PI 信号：取每位研究者被引最高的 100 篇论文，计算其为末位作者的占比。'
              '以色列理工科惯例是 PI 署名末位、学生署名首位，因此该比例越高越像课题组负责人。'
              f'本报告抽样 {pi.get("n", 0)} 人，中位数 {pi.get("median")}。', 9.8)

    h2(doc, '2.4 校验与误差')
    bullet(doc, f'PI 校验：A 层末位作者比例中位数 {pi.get("by_tier", {}).get("A", {}).get("median", "—")}，'
                f'C 层（对照组）{pi.get("by_tier", {}).get("C", {}).get("median", "—")}。'
                '对照组是刻意抽的博士生/博士后样本，差距就是分层规则的效度证据。')
    bullet(doc, 'PI 信号在大型合作组学科会失真：ATLAS/CMS 一类论文按字母序署名，'
                '末位作者没有“PI”含义，这类学者的 PI 指数会异常低（魏茨曼的物理样本即如此），'
                '因此不宜用 PI 指数跨学科、跨校比较。')
    oc = D.get('orcid_check') or {}
    if oc.get('n'):
        bullet(doc, f'ORCID 现职校验：{oc["n"]:,} 位 A 层有可解析的现职记录，其中明确为教授/副教授 '
                    f'{oc["professor"] + oc["associate"]:,} 人、讲师 {oc["lecturer"]:,} 人、'
                    f'博士后 {oc["postdoc"]:,} 人——说明 A 层里确实混入了少量资历较长的博士后，'
                    '但也有大量人只填了院系名称、无法归类，因此这是下界而非精确比例。')
    bullet(doc, '无官方职称时，A 层包含资深研究员、临床教授与部分长期工程师，也会漏掉新入职或极少发表者。')
    bullet(doc, '论文按篇计、一人一篇计一次；大科学合作组（ATLAS/CMS）会把个人数字推到数千篇。')
    bullet(doc, '2026 年收录不完整（滞后 3–9 个月），年度结论以 2025 年及以前为准。')

    quote_box(doc, '读这份报告的三条建议：① 先看第 1 章的集中度与专门化，判断这是“少数大 PI 型”还是“均衡型”学校；'
                   '② 找合作者只看第 6 章的后两张表（近三年产出、上升最快），不要用累计论文排序；'
                   '③ 任何跨校比较先回到第 2 章确认口径——官方名录与 OpenAlex 署名口径的人数不可直接相加。')


    # ---------------- 03 institution
    h1(doc, '03', '全校产出与结构')
    figure(doc, os.path.join(figd, 'years.png'),
           '图 1  年度论文产出（OpenAlex 机构口径，2016–2026）', width_cm=9.0)
    types = A['inst_types']
    oa = A['open_access']
    KEEP = ('article', 'review', 'preprint', 'conference-paper', 'book-chapter', 'book')
    top_types = sorted(((k, v) for k, v in types.items() if k in KEEP), key=lambda kv: -kv[1])[:4]
    para(doc, '论文类型以 ' + '、'.join(f'{k} {n(v)} 篇' for k, v in top_types)
              + f' 为主；开放获取占比 '
              f'{(oa["oa"]/oa["total"]*100) if oa["total"] else 0:.0f}%（{n(oa["oa"])} / {n(oa["total"])}）。'
              f' 机构口径十年论文总量 {n(C["institution_works_10y"])} 篇；'
              f'研究人口在同一窗口的署名次数为 {n(C["works_10y"])} 次——'
              '前者按篇计，后者按人-篇计，一篇多作者会被重复统计，因此后者大于前者是正常的。')

    topics = A.get('topics') or []
    if topics:
        h2(doc, '当前研究主题前 12 位')
        para(doc, '按 2016–2026 年署名该校的论文数排序，反映该校当前的研究构成（不是动态变化）。', 9.6)
        tot = sum(t['count'] for t in topics[:12]) or 1
        rows = [[t['name'][:56], n(t['count']), f'{t["count"]/ (sum(x["count"] for x in topics) or 1)*100:.1f}%']
                for t in topics[:12]]
        table(doc, ['OpenAlex 主题', '论文数', '占前 200 主题比重'], rows,
              widths=[9.6, 2.6, 3.6], font_size=8)

    countries = [c for c in A['countries'] if c['name'] != 'Israel'][:8]
    if countries:
        h2(doc, '国际合作的重心')
        table(doc, ['合作国', '合作论文计数'], [[c['name'], n(c['count'])] for c in countries],
              widths=[6.4, 6.2])
        para(doc, '', space_after=2)
        para(doc, f'最大合作方是 {countries[0]["name"]}（{n(countries[0]["count"])} 次），'
                  f'其后是 ' + '、'.join(c['name'] for c in countries[1:4]) + '。', 9.8)

    # ---------------- 04 domains
    h1(doc, '04', '学科结构')
    figure(doc, os.path.join(figd, 'domains.png'), '图 2  各研究领域人数')
    figure(doc, os.path.join(figd, 'works.png'), '图 3  各领域近十年论文总量')

    h2(doc, '相对十校平均的专门化程度')
    para(doc, '把本校每个领域的产出份额，除以十校同一领域的平均份额，得到专门化指数：'
              '>1.3 视为该校的特色强项，<0.7 视为相对薄弱。', 9.8)
    rows = [[s['domain_en'], f'{s["share"]*100:.0f}%', f'{s["ten_share"]*100:.0f}%',
             f'{s["index"]:.2f}', s['n']] for s in spec[:8]]
    table(doc, ['领域', '本校份额', '十校均值', '专门化指数', '人数'], rows,
          widths=[5.4, 2.4, 2.4, 2.6, 1.8])
    para(doc, '', space_after=2)
    if spec:
        para(doc, f'{spec[0]["domain_en"]} 的专门化指数 {spec[0]["index"]:.2f}，是本校最突出的方向；'
                  f'{spec[-1]["domain_en"]} 指数 {spec[-1]["index"]:.2f}，相对最弱。', 9.8)

    h2(doc, '分层 × 领域：资深力量分布在哪')
    rows = []
    for f in facs[:10]:
        a_n, b_n, c_n = f['A'], f['B'], f['C']
        tot = max(1, f['n'])
        rows.append([f['domain_en'], f['n'], a_n, b_n, c_n, f'{a_n/tot*100:.0f}%'])
    table(doc, ['研究领域', '人数', 'A 层', 'B 层', 'C 层', 'A 层占比'], rows,
          widths=[5.6, 2.2, 2.0, 2.0, 2.0, 2.4], font_size=8)
    para(doc, '', space_after=2)
    para(doc, 'A 层占比高的领域，通常意味着该领域以独立 PI 为主、团队规模大；'
              '占比低则多为大型实验组或学生主导的领域。', 8.8, False, MUTED)

    h2(doc, '各领域产出最高的 5 位')
    para(doc, '按研究领域分组、取近十年署名次数最高的 5 位，用于快速定位某一方向的带头人。', 9.4)
    bydom = {}
    for r in F:
        if r.get('tier') != 'A':
            continue
        d = r.get('domain_en') or 'Other'
        bydom.setdefault(d, []).append(r)
    rows = []
    for d in [f['domain_en'] for f in facs[:8]]:
        people = sorted(bydom.get(d, []), key=lambda x: -(x.get('works_10y') or 0))[:5]
        for k, r in enumerate(people):
            rows.append([d if k == 0 else '', r['name'], r.get('works_10y'),
                         r.get('works_2024_2026')])
    table(doc, ['研究领域', '姓名', '近十年署名', '近三年'], rows,
          widths=[4.6, 5.4, 3.2, 3.0], font_size=8)

    figure(doc, os.path.join(figd, 'growth.png'), '图 4  各领域前后五年产出对比')

    # ---------------- 05 topics
    h1(doc, '05', '研究主题的十年迁移')
    para(doc, f'对比 2016–2020 与 2021–2026 两个窗口，扣除全校总量增长（+{growth}%）后得到相对份额变化；'
              '只统计两窗口各 ≥15 篇、且都进入 OpenAlex 前 200 主题榜的主题。', 9.8)
    figure(doc, os.path.join(figd, 'up.png'), '图 5  份额上升最快的主题')
    if risers:
        para(doc, '上升侧集中在 ' + '、'.join(r['topic'] for r in risers[:3]) + '。'
                  f' 其中 {risers[0]["topic"]} 从 {risers[0]["early"]} 篇增至 {risers[0]["late"]} 篇，'
                  '是该校十年间最明显的方向性扩张。', 9.8)
    figure(doc, os.path.join(figd, 'down.png'), '图 6  份额下降最快的主题')
    if fallers:
        para(doc, '下降侧以 ' + '、'.join(f['topic'] for f in fallers[:3])
                  + ' 为主。份额下降不等于绝对产出下降，更多是其他方向增长更快所致。', 9.8)

    h2(doc, '绝对产出变化（前十主题）')
    top = sorted(mig, key=lambda m: -(m['early'] + m['late']))[:10]
    rows = [[m['topic'][:58], m['early'], m['late'], f'{m["rel_growth"]:+.0f}%'] for m in top]
    table(doc, ['主题', '2016-2020', '2021-2026', '相对增长'], rows,
          widths=[9.4, 2.4, 2.4, 2.4])
    figure(doc, os.path.join(figd, 'topics_heat.png'),
           '图 7  十大主题的绝对产出变化（用于核对份额变化是否被总量放大）')

    # ---------------- 06 people
    page_break(doc)
    h1(doc, '06', '人：谁值得优先联系')
    para(doc, '五张表分别看“学术积累”“当下强度”“上升速度”“代表作影响力”与“PI 指数”。'
              '找合作者与导师，中间三张比累计论文更有用。', 9.8)
    h2(doc, '6.1 近十年产出最高的 12 位')
    rows = [[p['name'], p['domain'], p['works'], p['recent'],
             (p['topics'][0] if p['topics'] else '')[:40]] for p in A['top_output'][:12]]
    table(doc, ['姓名', '领域', '署名次数', '近三年', '首要研究主题'], rows,
          widths=[3.6, 2.6, 1.2, 1.3, 7.5])

    h2(doc, '6.2 近三年产出最高的 12 位')
    rows = [[p['name'], p['domain'], p['recent'], p['works'],
             (p['topics'][0] if p['topics'] else '')[:40]] for p in A['top_recent'][:12]]
    table(doc, ['姓名', '领域', '近三年', '署名次数', '首要研究主题'], rows,
          widths=[3.6, 2.6, 1.3, 1.2, 7.5])

    if stars:
        h2(doc, '6.3 上升最快的研究者（近三年速度 ≥1.8× 前五年）')
        rows = [[s['name'], s['domain'], s['early'], s['recent'], s['works']] for s in stars[:10]]
        table(doc, ['姓名', '领域', '2016-2020', '2024-2026', '署名次数'], rows,
              widths=[4.6, 3.4, 2.6, 2.6, 2.2])
        para(doc, '', space_after=2)
        para(doc, '“上升”只表示产出加速，可能是新课题组起步，也可能是数据收录波动；'
                  '建议结合其研究主题与近期代表作判断。', 8.8, False, MUTED)

    s2_rows = [r for r in F if r.get('s2_influential') is not None]
    if s2_rows:
        h2(doc, '6.4 代表作与影响力引用（Semantic Scholar）')
        para(doc, '影响力引用（influential citations）只统计真正被后续研究采纳的引用，'
                  '比总被引更能区分“高被引”与“被用到”。下表按影响力引用排序，附代表作的一句话摘要。', 9.4)
        top = sorted(s2_rows, key=lambda r: -(r.get('s2_influential') or 0))[:8]
        rows = []
        for r in top:
            title = (r.get('s2_top_title') or '')[:52]
            tldr = (r.get('s2_top_tldr') or '')[:64]
            rows.append([r['name'], r.get('domain_en') or '', r.get('s2_influential'),
                         r.get('s2_citations'), f'{title} — {tldr}' if tldr else title])
        table(doc, ['姓名', '领域', '影响力引用', 'S2 被引', '代表作（标题 — 一句话摘要）'], rows,
              widths=[3.0, 2.2, 1.8, 1.6, 7.6], font_size=7.6)
        para(doc, '', space_after=2)
        para(doc, f'覆盖：本校 {len(s2_rows):,} 位 A 层研究者完成 Semantic Scholar 匹配；'
                  '影响力引用为所抽样论文的求和，抽样上限 100 篇。', 8.6, False, MUTED)

    pi_leaders = sorted([r for r in F if r.get('last_share') is not None and r.get('tier') == 'A'
                         and (r.get('works_10y') or 0) >= 10],
                        key=lambda r: -(r['last_share']))[:8]
    if pi_leaders:
        h2(doc, '6.5 PI 指数最高的 8 位（末位作者比例）')
        rows = [[r['name'], r.get('domain_en') or '', f'{r["last_share"]:.2f}',
                 r.get('works_10y'), r.get('pi_sampled')] for r in pi_leaders]
        table(doc, ['姓名', '领域', '末位作者比例', '署名次数', '样本篇数'], rows,
              widths=[5.0, 3.6, 2.8, 2.4, 2.0])

    # ---------------- 07 position among ten
    h1(doc, '07', '在十校中的位置')
    r0 = rank.get(code, {})
    if r0:
        def place(key):
            vals = sorted([x[key] for x in R if x.get(key) is not None], reverse=True)
            v = r0.get(key)
            if v is None or not vals:
                return '—'
            return f'{vals.index(v) + 1}/{len(vals)}'
        rows = [[x['name_zh'], x['population'], x['tier_A'], x['works'], x['per_capita_A'],
                 f'{x["top10_share"]*100:.0f}%', x['pi_median'], f'{x["growth"]}%']
                for x in sorted(R, key=lambda z: -z['population'])]
        table(doc, ['大学', '研究人口', 'A 层', '署名次数', 'A 层人均', '前10%占比', 'PI中位数', '五年增长'],
              rows, widths=[3.4, 2.0, 1.6, 2.2, 1.9, 1.9, 1.8, 1.8], font_size=7.6)
        para(doc, '', space_after=2)
        para(doc, f'本校在十校中的位次：研究人口第 {place("population")}、A 层人均署名第 '
                  f'{place("per_capita_A")}、前 10% 集中度第 {place("top10_share")}、'
                  f'五年增长第 {place("growth")}。', 9.8)

    # ---------------- 08 limits
    h1(doc, '08', '局限与使用建议')
    bullet(doc, '不能当作人事名录：A/B/C 与 PI 指数都是推断，不是职称、编制或任职年限。')
    bullet(doc, '不能跨校直接比人数：TAU 为官方名录口径，其余为 OpenAlex 署名口径。')
    bullet(doc, 'PI 信号依赖署名惯例：数学、人文与社会科学的末位作者制不成立，这些领域的 A 层可能被低估。')
    bullet(doc, '同名同姓与档案合并仍可能出错；高产出榜单已做主题一致性检查。')
    para(doc, '改进路径：拿到官方名录后替换分层；接入 FWCI 与经费数据后可从“产量”升级为“影响力与资源”。', 9.6)

    # ---------------- appendix
    h1(doc, 'A', '数据源与字段')
    rows = [['OpenAlex authors', '作者档案、主题、逐年产出', '研究人口与领域'],
            ['OpenAlex works（group_by）', '年度/主题/国别/类型/OA', '全校趋势'],
            ['OpenAlex works（作者抽样）', '被引前 100 篇的作者位次', 'PI 信号'],
            ['ROR ' + (A.get('ror') or ''), '机构标识', '口径核对']]
    table(doc, ['数据源', '内容', '用途'], rows, widths=[5.2, 7.0, 4.2], font_size=8)
    para(doc, '', space_after=3)
    h2(doc, '字段字典')
    fdict = [['works_10y', '近十年署名次数（人-篇）'],
             ['works_2016_2020 / works_2021_2026', '前后五年对比窗口'],
             ['works_2024_2026', '最近三年，判断当下强度'],
             ['works_total', 'OpenAlex 档案的生涯论文总数'],
             ['span', '发表跨度（年），首篇到末篇'],
             ['tier', 'A/B/C 分层结果'],
             ['last_share', '高被引论文中的末位作者比例（PI 信号）'],
             ['cite_per_work', '生涯篇均被引'],
             ['cite_per_work', '生涯篇均被引'],
             ['domain', '由 OpenAlex 主题推断的研究领域'],
             ['rising', '近三年速度 ≥1.8× 前五年'],
             ['orcid_role_class', 'ORCID 现职类型（教授/讲师/博士后等）']]
    seen = set()
    uniq = [r for r in fdict if not (r[0] in seen or seen.add(r[0]))]
    table(doc, ['字段', '含义'], uniq, widths=[5.6, 10.8], font_size=8)
    para(doc, '完整字段与逐人数据见合并主库（docs/insight_master.xlsx）的「02 合并主库」工作表。',
         8.8, False, MUTED)

    # ---------------- appendix B: ten-university table
    h1(doc, 'B', '附录：十校对比总表')
    rows = [[x['name_zh'], x['population'], x['tier_A'], x['works'], x['inst_works'],
             x['per_capita_A'], f'{x["top10_share"]*100:.0f}%', x['pi_median'], f'{x["growth"]}%']
            for x in sorted(R, key=lambda z: -z['population'])]
    table(doc, ['大学', '研究人口', 'A 层', '署名次数', '机构论文', 'A 层人均', '前10%', 'PI', '五年增长'],
          rows, widths=[3.2, 2.0, 1.5, 2.1, 2.1, 1.8, 1.3, 1.3, 1.7], font_size=7.4)
    para(doc, '', space_after=2)
    para(doc, '机构论文＝该校全部署名论文（按篇计）；署名次数＝研究人口逐人计数之和（一篇多作者重复计），'
              '两者不可直接相减。', 8.6, False, MUTED)

    out_docx = os.path.join(REPORTS, f'{code}_教授研究图谱.docx')
    doc.save(out_docx)
    return out_docx, code


def to_pdf(docx_path):
    pdf = docx_path[:-5] + '.pdf'
    if os.path.exists(pdf):
        os.remove(pdf)
    r = subprocess.run([NODE, CLI, 'convert', '--input', docx_path, '--output', pdf],
                       capture_output=True, timeout=300)
    ok = os.path.exists(pdf) and open(pdf, 'rb').read(5) == b'%PDF-'
    return ok, pdf, (r.stderr or b'')[-300:].decode('utf-8', 'replace')


def main():
    only = os.environ.get('UNIS', '').strip()
    os.makedirs(REPORTS, exist_ok=True)
    for uni in CONF['universities']:
        if only and uni['code'] not in only.split(','):
            continue
        try:
            d, code = build(uni)
            ok, pdf, err = to_pdf(d)
            size = os.path.getsize(pdf) // 1024 if os.path.exists(pdf) else 0
            print(f'[{code}] {"PDF ok" if ok else "PDF FAILED"} {size}KB {err if not ok else ""}', flush=True)
        except Exception as e:
            print(f'[{uni["code"]}] report FAILED: {type(e).__name__}: {e}', flush=True)


if __name__ == '__main__':
    main()
