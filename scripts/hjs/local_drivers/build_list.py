#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""从失败 CSV 生成 NAS 路径清单（每行一个），供 bookend 扫描。"""
import csv, sys

CSV = r'C:\Users\hjs78\Desktop\恢复失败记录_Photos.csv'
OUT = sys.argv[1] if len(sys.argv) > 1 else r'D:\WORK\failed_all.txt'
CATS = ('A 类（头部损坏', 'A 类（本次未还原', 'B 类（no-match', 'B 类（异常', 'B 类（解码失败')

paths = []
for r in csv.DictReader(open(CSV, encoding='utf-8-sig')):
    if r['类别'].startswith(CATS):
        p = r['NAS 路径'].replace('/homes/hjs', '/volume1/homes/hjs')
        paths.append(p)
open(OUT, 'w', encoding='utf-8').write('\n'.join(paths))
print(len(paths), 'paths ->', OUT)
