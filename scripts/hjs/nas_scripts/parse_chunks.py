#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""解析 btrfs-debug-tree -t 3 的 CHUNK_ITEM，建立 logical->physical 映射。"""
import re, sys, json

path = sys.argv[1]
chunks = []
cur = None
for line in open(path, 'r', encoding='utf-8', errors='ignore'):
    m = re.match(r'\s*item \d+ key \(FIRST_CHUNK_TREE CHUNK_ITEM (\d+)\)', line)
    if m:
        cur = {'l': int(m.group(1)), 'len': None, 'phys': None, 'type': None}
        chunks.append(cur)
        continue
    if cur is None:
        continue
    m = re.search(r'chunk length (\d+) owner \d+ stripe_len \d+', line)
    if m:
        cur['len'] = int(m.group(1))
        continue
    m = re.search(r'type (\S+) num_stripes', line)
    if m:
        cur['type'] = m.group(1)
        continue
    m = re.search(r'stripe 0 devid \d+ offset (\d+)', line)
    if m and cur['phys'] is None:
        cur['phys'] = int(m.group(1))

for c in chunks:
    assert c['len'] and c['phys'] is not None, c
    c['end'] = c['l'] + c['len']
json.dump(chunks, open(sys.argv[2], 'w'))

target = int(sys.argv[3]) if len(sys.argv) > 3 else None
print('chunks', len(chunks), 'total logical GB %.2f' % (sum(c['len'] for c in chunks) / 1e9))
if target is not None:
    for c in chunks:
        if c['l'] <= target < c['end']:
            print(json.dumps({'target': target, 'chunk': c,
                              'phys_of_target': c['phys'] + (target - c['l'])}))
            break
