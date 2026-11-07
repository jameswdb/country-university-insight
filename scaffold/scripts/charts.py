# -*- coding: utf-8 -*-
"""Small, dependency-light chart renderer (Pillow only).

The bundled Python has no matplotlib, so charts are drawn directly with PIL and
written as high-DPI PNGs for embedding in the DOCX workbook report. Style is kept
deliberately restrained: one accent colour, thin axes, direct labels, no chartjunk.

Chart types
  line_multi      - yearly series (one or more lines)
  bars_h          - horizontal bars with value labels (rankings)
  bars_v_grouped  - grouped vertical bars (faculties x two periods)
  stacked_share   - 100% stacked horizontal bar (activity mix)
"""
import os
from math import ceil
from PIL import Image, ImageDraw, ImageFont

W, H = 1800, 1000          # logical canvas, rendered at 2x for crisp print
S = 2                      # supersampling factor

INK = (28, 33, 40)
MUTED = (110, 119, 129)
GRID = (226, 230, 235)
ACCENT = (18, 84, 150)
ACCENT_RGB = (18, 84, 150)
ACCENT2 = (198, 106, 29)
ACCENT3 = (46, 139, 87)
ACCENT4 = (120, 86, 160)
PAPER = (255, 255, 255)

FONT_DIR = os.path.join(os.environ.get('WINDIR', r'C:\Windows'), 'Fonts')
F_BOLD = os.path.join(FONT_DIR, 'segoeuib.ttf')
F_REG = os.path.join(FONT_DIR, 'segoeui.ttf')
F_ZH = os.path.join(FONT_DIR, 'msyh.ttc')
F_ZH_BOLD = os.path.join(FONT_DIR, 'msyhbd.ttc')


def font(size, bold=False, zh=False):
    if zh:
        path = F_ZH_BOLD if bold else F_ZH
    else:
        path = F_BOLD if bold else F_REG
    return ImageFont.truetype(path, size * S)


def new_canvas(w=W, h=H):
    img = Image.new('RGB', (w * S, h * S), PAPER)
    return img, ImageDraw.Draw(img)


def save(img, path):
    img = img.resize((img.width // S, img.height // S), Image.LANCZOS)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    img.save(path, 'PNG')
    return path


def text(d, xy, s, f, fill=INK, anchor='la'):
    d.text((xy[0] * S, xy[1] * S), s, font=f, fill=fill, anchor=anchor)


def title_block(d, title, subtitle=None):
    text(d, (70, 48), title, font(40, True, zh=True))
    if subtitle:
        text(d, (70, 104), subtitle, font(22, False, zh=True), MUTED)


def nice_step(v):
    if v <= 0:
        return 1
    import math
    exp = math.floor(math.log10(v))
    base = 10 ** exp
    for m in (1, 2, 2.5, 5, 10):
        if v / (base * m) <= 4:
            return base * m
    return base * 10


def axes_frame(d, box, y_labels, y_max, y_min=0, fmt='{:.0f}', draw_x=True):
    x0, y0, x1, y1 = box
    n = max(1, len(y_labels) - 1)
    step = nice_step((y_max - y_min) / 4)
    n_ticks = max(2, ceil((y_max - y_min) / step))
    for i in range(n_ticks + 1):
        v = y_min + step * i
        y = y1 - (y1 - y0) * (v - y_min) / max(1e-9, (y_max - y_min))
        if v > y_max + 1e-9:
            continue
        d.line([(x0 * S, y * S), (x1 * S, y * S)], fill=GRID, width=1 * S)
        text(d, (x0 - 14, y), fmt.format(v), font(20, False), MUTED, anchor='rm')
    if draw_x:
        for i, lab in enumerate(y_labels):
            x = x0 + (x1 - x0) * i / n
            text(d, (x, y1 + 14), lab, font(21, False), MUTED, anchor='ma')
    d.line([(x0 * S, y1 * S), (x1 * S, y1 * S)], fill=(160, 168, 176), width=2 * S)


def line_multi(series, labels, title, subtitle, path, y_label='', colors=None,
               highlight_last=True, fmt='{:.0f}'):
    """series: dict label -> list of values (aligned to labels)."""
    img, d = new_canvas()
    title_block(d, title, subtitle)
    box = (150, 190, 1720, 850)
    vals = [v for s in series.values() for v in s if v is not None]
    y_max = max(vals) * 1.15 if vals else 1
    axes_frame(d, box, labels, y_max, 0, fmt)
    x0, y0, x1, y1 = box
    n = max(1, len(labels) - 1)
    colors = colors or [ACCENT, ACCENT2, ACCENT3, ACCENT4]
    for k, (name, vals2) in enumerate(series.items()):
        col = colors[k % len(colors)]
        pts = []
        for i, v in enumerate(vals2):
            if v is None:
                continue
            x = x0 + (x1 - x0) * i / n
            y = y1 - (y1 - y0) * (v / y_max if y_max else 0)
            pts.append((x, y))
        if len(pts) > 1:
            d.line([(x * S, y * S) for x, y in pts], fill=col, width=4 * S, joint='curve')
        for x, y in pts:
            d.ellipse([(x - 5) * S, (y - 5) * S, (x + 5) * S, (y + 5) * S], fill=col)
        if pts:
            lx, ly = pts[-1]
            text(d, (lx - 10, ly - 16), name, font(21, True, zh=True), col, anchor='rs')
    if y_label:
        text(d, (70, 130), y_label, font(21, False, zh=True), MUTED)
    return save(img, path)


def bars_h(items, title, subtitle, path, value_fmt='{:.0f}', color=ACCENT, top=18):
    """items: list of (label, value), already sorted desc."""
    items = items[:top]
    h = max(560, 150 + 46 * len(items))
    img, d = new_canvas(h=h)
    title_block(d, title, subtitle)
    # label column sized from the longest label (max 55% of canvas width)
    probe = font(22, False, zh=True)
    widest = max((d.textlength(str(l), font=probe) / S for l, _ in items), default=200)
    x0 = min(max(320, 70 + widest + 24), 980)
    x1 = 1660
    vmax = max((abs(v) for _, v in items), default=1) or 1
    y = 200
    for lab, v in items:
        bar_w = (x1 - x0) * (abs(v) / vmax)
        d.rectangle([x0 * S, y * S, (x0 + bar_w) * S, (y + 26) * S], fill=color)
        text(d, (x0 - 16, y + 13), lab, font(22, False, zh=True), INK, anchor='rm')
        text(d, (min(x0 + bar_w + 12, x1 + 6), y + 13), value_fmt.format(v),
             font(21, True), MUTED, anchor='lm')
        y += 46
    return save(img, path)


def bars_v_grouped(groups, series, title, subtitle, path, legend_y=160):
    """groups: x labels; series: dict name -> values."""
    img, d = new_canvas(h=1000)
    title_block(d, title, subtitle)
    box = (150, 210, 1720, 760)
    vals = [v for s in series.values() for v in s]
    y_max = max(vals) * 1.15 if vals else 1
    axes_frame(d, box, groups, y_max, 0, draw_x=False)
    x0, y0, x1, y1 = box
    g = len(groups)
    gw = (x1 - x0) / g
    colors = [ACCENT, ACCENT2, ACCENT3, ACCENT4]
    bw = gw * 0.8 / max(1, len(series))
    for si, (name, sv) in enumerate(series.items()):
        col = colors[si % len(colors)]
        for i, v in enumerate(sv):
            x = x0 + gw * i + gw * 0.1 + bw * si
            hh = (y1 - y0) * (v / y_max if y_max else 0)
            d.rectangle([x * S, (y1 - hh) * S, (x + bw * 0.92) * S, y1 * S], fill=col)
    # rotated category labels below the axis
    for i, g in enumerate(groups):
        words = str(g).replace('&', '& ').split()
        lines, cur = [], ''
        for w in words:
            if len(cur) + len(w) + 1 <= 13:
                cur = (cur + ' ' + w).strip()
            else:
                lines.append(cur)
                cur = w
        if cur:
            lines.append(cur)
        lines = lines[:3]
        cx = x0 + gw * i + gw / 2
        cy = y1 + 22
        for li, ln in enumerate(lines):
            timg = Image.new('RGBA', (400, 40), (0, 0, 0, 0))
            td = ImageDraw.Draw(timg)
            td.text((200, 20), ln, font=font(19, False, zh=True), fill=MUTED, anchor='mm')
            timg = timg.rotate(32, expand=1, resample=Image.BICUBIC)
            px = int(cx * S - timg.width / 2)
            py = int(cy * S + li * 22 * S - timg.height / 2)
            img.paste(timg, (px, py), timg)
        lx = x0 + 10 + si * 260
        d.rectangle([lx * S, legend_y * S, (lx + 20) * S, (legend_y + 18) * S], fill=col)
        text(d, (lx + 30, legend_y + 9), name, font(21, False, zh=True), INK, anchor='lm')
    return save(img, path)


def stacked_share(rows, title, subtitle, path, palette=None):
    """rows: list of (label, [(segment_name, value, color), ...])."""
    h = max(420, 170 + 54 * len(rows) + 70)
    img, d = new_canvas(h=h)
    title_block(d, title, subtitle)
    x0, x1 = 360, 1680
    y = 200
    used = []
    for lab, segs in rows:
        tot = sum(v for _, v, _ in segs) or 1
        text(d, (x0 - 16, y + 13), lab, font(22, True, zh=True), INK, anchor='rm')
        cx = x0
        for name, v, col in segs:
            w = (x1 - x0) * v / tot
            if w > 0:
                d.rectangle([cx * S, y * S, (cx + w) * S, (y + 26) * S], fill=col)
                if w > 46:
                    text(d, (cx + w / 2, y + 13), f'{v:,}', font(19, True), PAPER, anchor='mm')
            cx += w
            if name not in used:
                used.append(name)
            y_last = y
        y += 54
    lx = x0
    for name, col in [(n, c) for n, c in [(s[0], s[2]) for r in rows for s in r[1]]][:0]:
        pass
    seen = {}
    for _, segs in rows:
        for name, v, col in segs:
            seen[name] = col
    lx = x0
    for name, col in seen.items():
        d.rectangle([lx * S, (y + 8) * S, (lx + 20) * S, (y + 26) * S], fill=col)
        text(d, (lx + 30, y + 17), name, font(20, False, zh=True), INK, anchor='lm')
        lx += 210
    return save(img, path)


def heat(rows, cols, matrix, title, subtitle, path, fmt='{:.1f}', diverging=True):
    """matrix[i][j] numbers; rows/cols labels. Diverging blue/red around 0."""
    h = max(480, 210 + 44 * len(rows) + 60)
    img, d = new_canvas(h=h)
    title_block(d, title, subtitle)
    x0, y0 = 470, 190
    cw, ch = (1660 - x0) / max(1, len(cols)), 44
    vmax = max((abs(v) for r in matrix for v in r), default=1) or 1
    for j, c in enumerate(cols):
        text(d, (x0 + cw * j + cw / 2, y0 - 12), c, font(20, True, zh=True), MUTED, anchor='mm')
    mat = matrix if len(matrix) == len(rows) else list(map(list, zip(*matrix)))
    if len(mat) != len(rows):
        raise ValueError(f'heat(): {len(rows)} row labels vs {len(mat)} matrix rows')
    for i, r in enumerate(rows):
        lab = str(r)
        while d.textlength(lab, font=font(19, False, zh=True)) / S > (x0 - 100) and len(lab) > 8:
            lab = lab[:-2]
        if lab != str(r):
            lab = lab[:-1] + '…'
        text(d, (x0 - 14, y0 + ch * i + ch / 2), lab, font(19, False, zh=True), INK, anchor='rm')
        for j, v in enumerate(mat[i]):
            a = min(1.0, abs(v) / vmax)
            if diverging:
                col = (196, 60, 44) if v > 0 else (18, 84, 150)
                bg = tuple(int(255 - (255 - c) * a * 0.75) for c in col)
                fg = PAPER if a > 0.55 else INK
            else:
                bg = tuple(int(255 - (255 - c) * a * 0.8) for c in ACCENT_RGB)
                fg = PAPER if a > 0.55 else INK
            x, yy = x0 + cw * j, y0 + ch * i
            d.rectangle([x * S, yy * S, (x + cw - 3) * S, (yy + ch - 3) * S], fill=bg)
            text(d, (x + cw / 2, yy + ch / 2), fmt.format(v), font(20, True), fg, anchor='mm')
    return save(img, path)
