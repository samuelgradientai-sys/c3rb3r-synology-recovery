#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""解析 btrfs-debug-tree -t 10 的空闲空间树文本，得到空闲 extent 列表。"""
import re, sys, json

path = sys.argv[1]
pat = re.compile(r'FREE_SPACE_EXTENT (\d+)\)')
exts = []
with open(path, 'r', encoding='utf-8', errors='ignore') as f:
    for line in f:
        if 'FREE_SPACE_EXTENT' not in line:
            continue
        m = pat.search(line)
        if not m:
            continue
        # key (START FREE_SPACE_EXTENT LEN)
        k = line.split('key (', 1)[1].split(')', 1)[0].split()
        if len(k) < 3:
            continue
        exts.append((int(k[0]), int(k[2])))
s = sum(l for _, l in exts)
print(json.dumps({'count': len(exts), 'sum_gb': round(s / 1e9, 2),
                  'min_start': min(x[0] for x in exts), 'max_start': max(x[0] for x in exts),
                  'len_min': min(l for _, l in exts), 'len_max': max(l for _, l in exts)}))
json.dump(exts, open(sys.argv[2], 'w'))
