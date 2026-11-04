#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""bookend 收尾：检查失败清单里哪些已被救回，重写桌面文档。"""
import os, csv, glob, json, datetime
from docx import Document
from docx.shared import Pt, Cm
from docx.enum.section import WD_ORIENT

CSV_IN = r'C:\Users\hjs78\Desktop\恢复失败记录_Photos.csv'
DOCX = r'C:\Users\hjs78\Desktop\恢复失败记录_Photos.docx'
CSV_OUT = r'C:\Users\hjs78\Desktop\恢复失败记录_Photos.csv'
ROOTS = [r'E:\恢复数据_Photos\homes\hjs\Photos', r'D:\恢复数据_Photos\homes\hjs\Photos',
         r'F:\恢复数据_Photos\homes\hjs\Photos']
PREFIX = '/homes/hjs/Photos/'

rows = list(csv.DictReader(open(CSV_IN, encoding='utf-8-sig')))
print('input rows', len(rows))

kept = []
fixed = 0
for r in rows:
    nas = r['NAS 路径']
    rel = nas.replace(PREFIX, '')
    if rel.endswith('.L0CK3D'):
        rel = rel[:-7]
    rel = rel.replace('/', os.sep)
    hit = False
    for root in ROOTS:
        p = os.path.join(root, rel)
        if os.path.isfile(p):
            # 损坏待修复目录里的不算救回
            if '_损坏待修复' in p:
                continue
            hit = True
            break
    if hit:
        fixed += 1
    else:
        kept.append(r)

print('recovered by bookend:', fixed, 'remaining failures:', len(kept))

with open(CSV_OUT, 'w', encoding='utf-8-sig', newline='') as f:
    w = csv.DictWriter(f, fieldnames=['类别', '文件名', 'NAS 路径', '不能解密原因'])
    w.writeheader()
    w.writerows(kept)

# 统计
from collections import Counter
c = Counter(r['类别'] for r in kept)

doc = Document()
sec = doc.sections[0]
sec.orientation = WD_ORIENT.LANDSCAPE
sec.page_width, sec.page_height = sec.page_height, sec.page_width
sec.left_margin = sec.right_margin = Cm(1.2)
doc.add_heading('C3RB3R 加密文件恢复失败记录（Photos·最终版）', level=0)
doc.add_paragraph('生成时间：%s' % datetime.datetime.now().strftime('%Y-%m-%d %H:%M'))
doc.add_paragraph('本轮通过“旧根 bookend”方案又从失败清单中救回 %d 个文件。' % fixed)
doc.add_paragraph('当前仍未恢复：共 %d 个。' % len(kept))
for k, v in c.most_common():
    doc.add_paragraph('  %s：%d 个' % (k, v))
doc.add_paragraph('')
doc.add_paragraph('已恢复总量：A 类 22,314 + B 类 410 + C 类 68,459 + bookend %d（约 500 GB）。' % fixed)


def add_table(title, data, note, limit=None):
    doc.add_heading(title, level=1)
    doc.add_paragraph(note)
    t = doc.add_table(rows=1, cols=3)
    t.style = 'Table Grid'
    h = t.rows[0].cells
    h[0].text, h[1].text, h[2].text = '文件名', 'NAS 路径', '不能解密原因'
    for r in (data if limit is None else data[:limit]):
        cell = t.add_row().cells
        cell[0].text = r['文件名']
        cell[1].text = r['NAS 路径']
        cell[2].text = r['不能解密原因']
    for row in t.rows:
        for cell in row.cells:
            for par in cell.paragraphs:
                for run in par.runs:
                    run.font.size = Pt(7)
    if limit and len(data) > limit:
        doc.add_paragraph('（仅列前 %d 条，全部见 CSV）' % limit)


for cat in ['A 类（头部损坏待修复）', 'A 类（本次未还原）', 'B 类（no-match）', 'B 类（解码失败）',
            'B 类（异常）', 'C 类（0x24，未找到）']:
    sub = [r for r in kept if r['类别'] == cat]
    if sub:
        add_table('%s（%d 个）' % (cat, len(sub)), sub, '仍未恢复，原因见下表。', limit=300)

doc.save(DOCX)
print('docx saved; remaining', len(kept))
json.dump({'fixed': fixed, 'remaining': len(kept), 'by_cat': dict(c)},
          open(r'D:\WORK\日志\bookend_final.json', 'w', encoding='utf-8'), ensure_ascii=False)
