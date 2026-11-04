#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""检查 C 类候选：解码、格式、重复内容、尺寸分布。"""
import os, hashlib, json
from collections import Counter, defaultdict
from PIL import Image

ROOT = r'F:\恢复数据_ljw_C'
OUT = os.path.join(ROOT, '候选检查报告.txt')

stats = {}
hashes = defaultdict(list)
bad = []
for sub in ('恢复结果', '候选'):
    d = os.path.join(ROOT, sub)
    n = ok = 0
    dims = Counter()
    exts = Counter()
    for dp, dn, fn in os.walk(d):
        for f in fn:
            p = os.path.join(dp, f)
            n += 1
            ext = os.path.splitext(f)[1].lower()
            exts[ext] += 1
            try:
                im = Image.open(p)
                im.load()
                ok += 1
                dims[im.size] += 1
                h = hashlib.md5(open(p, 'rb').read()).hexdigest()
                hashes[h].append(os.path.join(sub, os.path.relpath(p, d)))
            except Exception:
                bad.append(os.path.join(sub, os.path.relpath(p, d)))
    stats[sub] = (n, ok, exts, dims.most_common(5))

dups = {h: v for h, v in hashes.items() if len(v) > 1}

L = []
L.append('C 类恢复结果检查')
L.append('')
for sub, (n, ok, exts, dims) in stats.items():
    L.append('【%s】%d 个文件，可解码 %d（%.1f%%）' % (sub, n, ok, ok * 100.0 / max(n, 1)))
    L.append('  扩展名：%s' % dict(exts.most_common(6)))
    L.append('  常见尺寸：%s' % dims)
    L.append('')
L.append('重复内容组：%d 组（同内容写了多个文件名）' % len(dups))
mx = sorted(dups.items(), key=lambda x: -len(x[1]))[:5]
for h, v in mx:
    L.append('  %d 个同内容：%s' % (len(v), v[:2]))
L.append('')
L.append('解码失败：%d 个' % len(bad))
for b in bad[:10]:
    L.append('  ' + b)
if bad:
    open(os.path.join(ROOT, '解码失败清单.txt'), 'w', encoding='utf-8').write('\n'.join(bad))

open(OUT, 'w', encoding='utf-8').write('\n'.join(L))
print('\n'.join(L[:20]))
print('dups', len(dups), 'bad', len(bad))
