#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""把空闲 extent(逻辑) 映射成设备物理区间，合并相邻，输出 'offset length' 列表。"""
import json, sys

chunks = json.load(open(sys.argv[1]))
free = json.load(open(sys.argv[2]))
minlen = int(sys.argv[3])
out = sys.argv[4]

chunks.sort(key=lambda c: c['l'])
ranges = []
skipped = 0
for s, l, g in free:
    if l < minlen:
        skipped += 1
        continue
    # 找到包含 s 的 chunk（chunk 内物理连续）
    import bisect
    starts = [c['l'] for c in chunks]
    i = bisect.bisect_right(starts, s) - 1
    ok = False
    while i >= 0 and i < len(chunks):
        c = chunks[i]
        if c['l'] <= s < c['end']:
            # 该 extent 是否整个落在 chunk 内
            e = min(s + l, c['end'])
            ranges.append((c['phys'] + (s - c['l']), e - s))
            if e - s < l:
                ranges.append((None, 0))  # 跨 chunk，标记（本不该发生）
            ok = True
            break
        if s >= c['end']:
            i += 1
        else:
            i -= 1
    if not ok:
        skipped += 1

ranges = [r for r in ranges if r[0] is not None]
ranges.sort()
merged = []
for off, ln in ranges:
    if merged and merged[-1][0] + merged[-1][1] == off:
        merged[-1][1] += ln
    else:
        merged.append([off, ln])
with open(out, 'w') as f:
    for off, ln in merged:
        f.write('%d %d\n' % (off, ln))
print('free extents', len(free), 'used', len(ranges), 'merged ranges', len(merged),
      'GB %.2f' % (sum(r[1] for r in merged) / 1e9), 'skipped', skipped)
