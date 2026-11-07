---
name: country-university-insight
description: 输入一个国家，产出该国 TOP 高校的教授/研究人员图谱：可筛选合并主库（Excel）+ 每校一份 PDF 深度报告 + 十校/多校对比报告。覆盖人员口径核查、近十年论文与主题迁移、PI 信号、集中度与学科专门化、ORCID 职业轨迹、可选的 Semantic Scholar 影响力引用。当用户说“洞察某国的高校/教授”“做某国 top 大学的研究图谱”“分析某国大学的教授与研究方向”，或给出国家名并要求高校/学者/论文分析时使用。
---

# 国家高校与教授图谱（Country University Insight）

输入一个国家 → 输出该国头部大学的教授名录、研究领域与十年研究变迁，并合并成一个可筛选主库。

## 何时用

- 用户给一个国家（中文名、英文名或 ISO-2 代码），想看该国 **top N 高校的教授/研究者**、**研究方向**、**近十年变化**。
- 用户要“合并主库 + 每校报告 + 多校对比”这类交付。
- 用户想找**合作者 / 招生导师 / 对标学者**，需要“领域 + 活跃度 + 近期论文”的筛选表。

不适用：单个学者画像（直接查 OpenAlex 即可）、纯排名需求（本 skill 以研究产出为口径，不是官方排名）。

## 必须先问用户的三件事（不要替用户决定）

按顺序问，一次只问必要的：

1. **范围**：国家 + 头部高校数量（默认 10）+ 是否需要“只做研究型大学（不含学院）”。
2. **凭据**（单独问，强调只放在环境变量里，不写进任何文件、不提交到仓库）：
   - `OPENALEX_API_KEY`：**强烈建议**。没有 key 时额度极小（约 $0.10/天），只能跑 1–2 所学校。
   - `S2_API_KEY`（可选）：Semantic Scholar，用于影响力引用与 TLDR；没有就跳过该增强。
   - GitHub token（仅当用户要上传时问）：需要 `Contents: Read and write`；要建新仓库还需 `Administration: Read and write`。
3. **是否上传 GitHub**：**单独确认**。用户没明确说“上传/发布”，就不要 push；即使说了，也先确认“仓库名、public 还是 private、上传哪些文件（PDF+Excel+脚本，还是只 PDF）”。

如果用户拒绝提供 key，就退化为“只跑 1–2 所学校 + 说明额度限制”，不要硬跑全量。

## 工作流

在用户的工作区里建一个项目目录（例如 `./insight/`），把 `scaffold/` 复制进去：

```
scaffold/
├── config/universities.example.json
└── scripts/   00_discover.py … 12_s2_merge.py, charts.py, domains.py
```

### 0. 建项目

```bash
mkdir -p insight && cp -r <skill>/scaffold/* insight/ && cd insight
```

### 1. 确定国家与学校清单

```bash
export OPENALEX_API_KEY=...
python scripts/00_discover.py --country IL --top 10
```

输出按 OpenAlex `works_count` 排序的机构表（已剔除基金会、医院、friends-of 等）。**把这张表给用户看，允许替换/删除条目**，再继续——后面的下载很贵，错了要重跑。

口径要在报告里写清：这是“研究产出体量”口径，不是 QS/THE 排名；用户若指定排名，按其名单手工改 `config/universities.json`。

### 2. 抓取与建模（可直接跑，勿跳步）

```bash
python scripts/01_download.py     # 每校作者档案（≥2 篇），断点续跑
python scripts/02_trends.py       # 机构级年度/主题/国别/类型/OA 聚合
python scripts/03_analyze.py      # A/B/C 分层、领域归属、排行榜
python scripts/04_figures.py      # 每校 7 张图
```

分层规则（写进报告，不要当成官方职称）：A = 发表跨度 ≥12 年且 ≥12 篇；B = ≥9 年且 ≥8 篇；C = 其余。领域由 OpenAlex 主题推断。

### 3. 可选增强

```bash
# ORCID：现职、任职经历、学历（无需 key，公开 API）
python scripts/10_orcid.py

# Semantic Scholar：影响力引用 + 代表作 TLDR（需要 S2_API_KEY；先小样本验证匹配率）
S2_API_KEY=... TOP=40 LIMIT=40 python scripts/11_semantic_scholar.py
python scripts/12_s2_merge.py
```

先跑 `LIMIT=40` 看匹配率（实测约 97%），再决定是否放大。`TOP=0` 表示只取指标不取代表作。

### 4. 生成交付物

```bash
python scripts/05_report.py       # 每校一份 DOCX → PDF
python scripts/06_master.py       # 合并主库 xlsx
python scripts/07_overview.py     # 多校对比 PDF
```

### 5. 交付前自检

- 每份 PDF 的页数是否合理（单校 12–14 页）；有无空白页、表格串页。
- 主库里 `tier`、`domain`、`prov` 三列是否有空值。
- 报告中所有“论文数”是否区分了**机构口径（按篇）**与**署名次数（人-篇）**——这两个数不能相等，必须分别标注。
- 报告是否注明：2026 年数据不完整，趋势结论用 2016–2025。

### 6. 上传 GitHub（仅当用户确认）

```bash
git init && git add -A && git commit -m "…"
git remote add origin https://<token>@github.com/<user>/<repo>.git
git push -u origin main
```

- token 只出现在命令里，**不要写进 `.git/config` 以外的任何文件**；交付前 `git status` 确认没有 `.env`、key、原始缓存被提交。
- 默认 `private`；公开要用户明确同意。
- 仓库里放大文件（PDF/Excel），`data/raw/`、`out/figs/` 用 `.gitignore` 排除。

## 交付物

```
insight/
├── docs/<country>_master.xlsx     合并主库（每校 sheet + 全量 sheet + 领域矩阵 + 专门化 + 主题迁移）
├── reports/<CODE>_report.pdf      每校一份
├── reports/00_overview.pdf        多校对比
├── scripts/                       全流程脚本
└── README.md                      口径、发现、复现、局限
```

## 硬性约束（写进报告，不要美化）

1. **人员口径**：只有少数学校有公开可批量获取的官方名录（如 TAU 的希伯来语通讯录）。其余学校用 OpenAlex 署名作者（last-known 机构 + ≥6 篇）推断，**不是人事编制**。两种口径的人数不可相加。
2. **不要抓取 LinkedIn**：无凭据，且其用户协议禁止自动化访问。用 ORCID 代替职业轨迹。
3. **不要绕过 CRIS/Cloudflare**：多数以色列/欧洲高校的 Pure CRIS 有防护且需机构 key；探测到 403 就如实记录“不可得”，不要尝试绕过。
4. **计数陷阱**：大科学合作组（ATLAS/CMS、部分基因组联盟）单篇数百至数千作者，会把个人“署名次数”推到数千，必须与“论文数”分列。
5. **同名同姓**：英文名匹配必然有残余误配，高产出榜单需主题一致性抽查；报告里给出置信度或下界。

## 参考

- `references/methodology.md`：指标定义、分层规则、验证方法、报告章节结构。
- `references/pitfalls.md`：本 skill 从实战中踩过的坑（字段不合法、表格宽度、限流、时区、页数崩坏等），动手前先读。
