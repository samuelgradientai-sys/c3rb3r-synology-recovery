#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""生成恢复统计 Excel（按大小分层 + 类型）。"""
import json
from openpyxl import Workbook
from openpyxl.styles import Font, Alignment, PatternFill, Border, Side
from openpyxl.utils import get_column_letter

orig = {s: json.load(open(r'D:\WORK\日志\sizes_%s.json' % s, encoding='utf-8-sig'))
        for s in ('hjs', 'ljw', 'lsq')}
rec = json.load(open(r'D:\WORK\日志\recovered_sizes.json', encoding='utf-8'))
OUT = r'C:\Users\hjs78\Desktop\恢复统计_按大小类型.xlsx'

BUCKETS = [('lt1m', '小于 1 MB'), ('1to128m', '1 – 128 MB'), ('gt128m', '大于 128 MB')]
TYPES = [('image', '图片'), ('video', '视频'), ('other', '其他（索引/侧车）')]
HEAD_FILL = PatternFill('solid', fgColor='1F4E78')
HEAD_FONT = Font(color='FFFFFF', bold=True, size=11)
TITLE_FONT = Font(bold=True, size=14)
SUB_FILL = PatternFill('solid', fgColor='DDEBF7')
THIN = Side(style='thin', color='BFBFBF')
BORDER = Border(left=THIN, right=THIN, top=THIN, bottom=THIN)


def get(d, b, t):
    return d.get('%s|%s' % (b, t), {'count': 0, 'bytes': 0})


def agg(shares, b, t):
    n = by = rn = rb = 0
    for s in shares:
        o = get(orig[s], b, t)
        r = get(rec.get(s, {}), b, t)
        n += o['count']; by += o['bytes']
        rn += r['count']; rb += r['bytes']
    return n, by, rn, rb


wb = Workbook()


def build_sheet(ws, title, shares):
    ws['A1'] = title
    ws['A1'].font = TITLE_FONT
    ws.merge_cells('A1:I1')
    ws['A2'] = '原数据量 = NAS 加密文件原始大小；恢复数据量 = 已通过解码校验的文件大小'
    ws['A2'].font = Font(size=9, italic=True, color='666666')
    ws.merge_cells('A2:I2')

    heads = ['大小区间', '类型', '原文件数', '原大小(GB)', '恢复文件数', '恢复大小(GB)', '文件成功率', '字节成功率']
    for c, h in enumerate(heads, 1):
        cell = ws.cell(row=4, column=c, value=h)
        cell.fill = HEAD_FILL
        cell.font = HEAD_FONT
        cell.alignment = Alignment(horizontal='center', vertical='center')
        cell.border = BORDER

    row = 5
    tot = [0, 0, 0, 0]
    for b, bl in BUCKETS:
        start_row = row
        for t, tl in TYPES:
            n, by, rn, rb = agg(shares, b, t)
            if n == 0:
                continue
            vals = [bl, tl, n, by / 1e9, rn, rb / 1e9,
                    rn / n if n else 0, rb / by if by else 0]
            for c, v in enumerate(vals, 1):
                cell = ws.cell(row=row, column=c, value=v)
                cell.border = BORDER
                if c in (3, 5):
                    cell.number_format = '#,##0'
                elif c in (4, 6):
                    cell.number_format = '0.00'
                elif c in (7, 8):
                    cell.number_format = '0.0%'
            row += 1
            tot[0] += n; tot[1] += by; tot[2] += rn; tot[3] += rb
        if row - start_row > 1:
            ws.merge_cells(start_row=start_row, start_column=1, end_row=row - 1, end_column=1)
            ws.cell(row=start_row, column=1).alignment = Alignment(vertical='center', horizontal='center')
        for c in range(1, 9):
            ws.cell(row=start_row, column=c).fill = SUB_FILL

    vals = ['合计', '', tot[0], tot[1] / 1e9, tot[2], tot[3] / 1e9,
            tot[2] / tot[0] if tot[0] else 0, tot[3] / tot[1] if tot[1] else 0]
    for c, v in enumerate(vals, 1):
        cell = ws.cell(row=row, column=c, value=v)
        cell.font = Font(bold=True)
        cell.fill = PatternFill('solid', fgColor='FFF2CC')
        cell.border = BORDER
        if c in (3, 5):
            cell.number_format = '#,##0'
        elif c in (4, 6):
            cell.number_format = '0.00'
        elif c in (7, 8):
            cell.number_format = '0.0%'

    widths = [16, 18, 12, 13, 12, 13, 11, 11]
    for i, w in enumerate(widths, 1):
        ws.column_dimensions[get_column_letter(i)].width = w
    ws.freeze_panes = 'A5'


ws = wb.active
ws.title = '合计'
build_sheet(ws, 'C3RB3R 恢复统计（hjs + ljw + lsq 合计）', ['hjs', 'ljw', 'lsq'])
for s, name in (('hjs', 'hjs'), ('ljw', 'ljw'), ('lsq', 'lsq')):
    build_sheet(wb.create_sheet(name), 'C3RB3R 恢复统计（%s）' % name, [s])

# 说明页
ws = wb.create_sheet('说明')
notes = [
    ('统计口径', ''),
    ('原数据量', 'NAS 上 .L0CK3D 文件尾部的原始大小 N 字段（不是加密后文件大小）'),
    ('恢复数据量', '本地已恢复到磁盘、并通过完整解码校验的文件实际大小'),
    ('文件成功率', '恢复文件数 / 原文件数'),
    ('字节成功率', '恢复字节数 / 原字节数'),
    ('', ''),
    ('为什么 >128MB 字节成功率低', '丢掉的是体积最大的几个视频（单个 3–8 GB），每丢一个就少几十 GB'),
    ('为什么 <1MB 图片成功率低', '这批是 @eaDir 缩略图，整文件加密、原始块易被覆盖'),
    ('为什么 <1MB 视频是 0%', 'C 类雕刻只识别 JPEG/PNG 头部，未处理 mp4/mov（共 249 个 / 0.18 GB）'),
    ('“其他”是什么', 'SYNOPHOTO_INDEX、.db 等索引/侧车文件，无照片价值'),
]
ws['A1'] = '指标说明'
ws['A1'].font = TITLE_FONT
for i, (k, v) in enumerate(notes, 3):
    ws.cell(row=i, column=1, value=k).font = Font(bold=True)
    ws.cell(row=i, column=2, value=v)
ws.column_dimensions['A'].width = 30
ws.column_dimensions['B'].width = 70

wb.save(OUT)
print('saved', OUT)
