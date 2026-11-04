#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""C 类雕刻：在空闲空间镜像中按已知原始长度 N 寻找完整文件（JPEG/PNG）。

free.bin 由 raw_reader.py 生成：每个区间 = 12 字节头(<QI phys,len>) + 数据。
"""
import os, sys, struct, json, bisect
from collections import defaultdict

FREE = r'D:\恢复数据C\free.bin'
RANGES = r'D:\恢复数据C\ranges_all.txt'
LIST = r'D:\恢复数据C\list_024.tsv'
REPORT = r'D:\恢复数据C\carve_cands.json'

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
total = off
print('frames', len(frames), 'stream GB %.2f' % (total / 1e9))

files = defaultdict(list)
nfmt = defaultdict(set)
ext_fmt = {'.jpg': 'jpeg', '.jpeg': 'jpeg', '.png': 'png'}
with open(LIST, encoding='utf-8') as f:
    for line in f:
        line = line.rstrip('\n')
        if not line:
            continue
        rel, n = line.split('\t')
        n = int(n)
        base = rel[:-len('.L0CK3D')] if rel.endswith('.L0CK3D') else rel
        fmt = ext_fmt.get(os.path.splitext(base)[1].lower())
        if not fmt:
            continue
        files[(fmt, n)].append(rel)
        nfmt[fmt].add(n)
print('target image files', sum(len(v) for v in files.values()), 'unique (fmt,N)', len(files))

JPEG_SOI = b'\xff\xd8\xff'
JPEG_EOI = b'\xff\xd9'
PNG_SIG = b'\x89PNG\r\n\x1a\n'
PNG_END = b'IEND\xae\x42\x60\x82'
MAXLEN = 2 * 1024 * 1024
BLK = 16 << 20

cands = []
with open(FREE, 'rb') as f:
    buf = b''
    base = 0
    while True:
        blk = f.read(BLK)
        if not blk:
            break
        buf = buf + blk
        i = 0
        consumed = None
        while True:
            j = buf.find(JPEG_SOI, i)
            k = buf.find(PNG_SIG, i)
            pos = -1
            fmt = None
            if j >= 0 and (k < 0 or j < k):
                pos, fmt = j, 'jpeg'
            elif k >= 0:
                pos, fmt = k, 'png'
            if pos < 0:
                consumed = len(buf)
                break
            if fmt == 'jpeg':
                e = buf.find(JPEG_EOI, pos + 3)
                need = e + 2 if e >= 0 else -1
            else:
                e = buf.find(PNG_END, pos + 8)
                need = e + 8 if e >= 0 else -1
            if need < 0:
                consumed = pos          # 等下一块再判断
                break
            ln = need - pos
            if 512 <= ln <= MAXLEN:
                abs_off = base + pos
                fi = bisect.bisect_right(fstarts, abs_off) - 1
                if fi >= 0:
                    fphys, flen = frames[fi]
                    if abs_off + ln <= fstarts[fi] + flen:
                        if ln in nfmt[fmt]:
                            phys = fphys + (abs_off - fstarts[fi])
                            cands.append([fmt, phys, ln])
            i = pos + 3
            if i >= len(buf):
                consumed = len(buf)
                break
        consumed = consumed if consumed is not None else len(buf)
        base += consumed
        buf = buf[consumed:]
        if base % (1 << 30) < BLK:
            print('scanned %.1f GB  cands %d' % (base / 1e9, len(cands)), flush=True)

print('candidates', len(cands))
json.dump(cands, open(REPORT, 'w'))
