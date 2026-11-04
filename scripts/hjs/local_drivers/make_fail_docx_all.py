#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""按合并后的失败 CSV 重新生成 Word 文档。"""
import csv, datetime
from collections import Counter
from docx import Document
from docx.shared import Pt, Cm
from docx.enum.section import WD_ORIENT

CSV = r'C:\Users\hjs78\Desktop\恢复失败记录_Photos.csv'
DOCX = r'C:\Users\hjs78\Desktop\恢复失败记录_Photos.docx'

rows = list(csv.DictReader(open(CSV, encoding='utf-8-sig')))
c = Counter(r['类别'] for r in rows)

ORDER = ['A 类（头部损坏待修复）', 'A 类（本次未还原）', 'B 类（no-match）', 'B 类（解码失败）',
         'B 类（异常）', 'C 类（0x24，未找到）',
         'ljw A 类（旧 extent 不可用）', 'ljw B 类（大视频未还原）', 'ljw C 类（0x24 未找到）',
         'lsq C 类（0x24 未找到）']

doc = Document()
sec = doc.sections[0]
sec.orientation = WD_ORIENT.LANDSCAPE
sec.page_width, sec.page_height = sec.page_height, sec.page_width
sec.left_margin = sec.right_margin = Cm(1.2)

doc.add_heading('C3RB3R 加密文件恢复失败记录（总表）', level=0)
doc.add_paragraph('生成时间：%s' % datetime.datetime.now().strftime('%Y-%m-%d %H:%M'))
doc.add_paragraph('覆盖范围：/homes/hjs/Photos、/homes/ljw/Photos、/homes/lsq/Photos')
doc.add_paragraph('仍未恢复合计：%d 个' % len(rows))
doc.add_paragraph('')
for k, v in c.most_common():
    doc.add_paragraph('  %s：%d 个' % (k, v))
doc.add_paragraph('')
doc.add_paragraph('已恢复总量：hjs 92,250 个 / 484 GB；ljw 32,501 个 / 57.8 GB；lsq 525 个 / 1.1 GB。')
doc.add_paragraph('说明：每个“已恢复”文件都通过完整解码校验；表中为仍无法恢复的文件。')

for cat in ORDER:
    sub = [r for r in rows if r['类别'] == cat]
    if not sub:
        continue
    doc.add_heading('%s（%d 个，下表最多列 300 条）' % (cat, len(sub)), level=1)
    t = doc.add_table(rows=1, cols=3)
    t.style = 'Table Grid'
    h = t.rows[0].cells
    h[0].text, h[1].text, h[2].text = '文件名', 'NAS 路径', '原因'
    for r in sub[:300]:
        cell = t.add_row().cells
        cell[0].text = r['文件名']
        cell[1].text = r['NAS 路径']
        cell[2].text = r['不能解密原因']
    for row in t.rows:
        for cell in row.cells:
            for par in cell.paragraphs:
                for run in par.runs:
                    run.font.size = Pt(7)

doc.save(DOCX)
print('docx saved', len(rows))
