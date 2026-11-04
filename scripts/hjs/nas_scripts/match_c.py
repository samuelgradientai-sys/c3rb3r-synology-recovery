#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""C 类匹配与落盘：把雕刻到的候选按 (格式, 长度) 与 0x24 文件配对。"""
import os, sys, struct, bisect, json, hashlib
from collections import defaultdict
from PIL import Image

FREE = r'D:\恢复数据C\free.bin'
RANGES = r'D:\恢复数据C\ranges_all.txt'
CAND = r'D:\恢复数据C\carve_cands.json'
LIST = r'D:\恢复数据C\list_024.tsv'
OUT_CERTAIN = r'D:\恢复数据C\恢复结果'
OUT_MAYBE = r'D:\恢复数据C\候选_名字不确定'
REPORT = r'D:\恢复数据C\match_report.json'

frames = []
with open(RANGES) as f:
    for line in f:
        a, b = line.split()
        frames.append((int(a), int(b)))
fstarts = []
off = 0
for a, b in frames:
    off += 12
    fstarts.append(off)
    off += b
fphys = [a for a, b in frames]

cands = json.load(open(CAND))
by = defaultdict(list)
for fmt, phys, ln in cands:
    by[(fmt, ln)].append(phys)

files = defaultdict(list)
with open(LIST, encoding='utf-8') as f:
    for line in f:
        line = line.rstrip('\n')
        if not line:
            continue
        rel, n = line.split('\t')
        n = int(n)
        base = rel[:-len('.L0CK3D')] if rel.endswith('.L0CK3D') else rel
        fmt = {'.jpg': 'jpeg', '.jpeg': 'jpeg', '.png': 'png'}.get(os.path.splitext(base)[1].lower())
        if fmt:
            files[(fmt, n)].append(rel)

certain = 0
maybe = 0
missing = 0
verified_fail = 0
written = 0
sizes = 0

fh = open(FREE, 'rb')


def read_cand(phys, ln):
    i = bisect.bisect_right(fphys, phys) - 1
    if i < 0:
        raise ValueError('phys')
    foff = fstarts[i] + (phys - fphys[i])
    fh.seek(foff)
    return fh.read(ln)


def save(rel, data, root):
    dst = os.path.join(root, rel[:-len('.L0CK3D')].replace('/', os.sep))
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    with open(dst, 'wb') as o:
        o.write(data)
    return dst


for key, rels in files.items():
    cps = sorted(by.get(key, []))
    rels = sorted(rels)
    if not cps:
        missing += len(rels)
        continue
    n = min(len(cps), len(rels))
    for k in range(n):
        data = read_cand(cps[k], key[1])
        ok = True
        if key[0] in ('jpeg', 'png'):
            try:
                import io
                im = Image.open(io.BytesIO(data)); im.load()
            except Exception:
                ok = False
        if not ok:
            verified_fail += 1
            continue
        is_certain = (len(cps) == 1 and len(rels) == 1)
        save(rels[k], data, OUT_CERTAIN if is_certain else OUT_MAYBE)
        written += 1
        sizes += len(data)
        if is_certain:
            certain += 1
        else:
            maybe += 1
    if len(cps) < len(rels):
        missing += len(rels) - len(cps)

fh.close()
json.dump({'certain': certain, 'maybe': maybe, 'missing': missing,
           'verify_fail': verified_fail, 'written': written, 'bytes': sizes},
          open(REPORT, 'w', encoding='utf-8'), ensure_ascii=False)
print(json.dumps({'certain': certain, 'maybe': maybe, 'missing': missing,
                  'verify_fail': verified_fail, 'written': written,
                  'GB': round(sizes / 1e9, 2)}))
