#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""流式输出空闲空间：每段 12 字节头 + 固定长度数据；读取失败补零，保证帧对齐。"""
import sys, os, struct

dev = os.open('/dev/mapper/cachedev_0', os.O_RDONLY)
out = sys.stdout.buffer
total = 0
bad = 0
with open('/tmp/_dsh_ranges.txt') as f:
    for line in f:
        p = line.split()
        if len(p) != 2:
            continue
        a, b = int(p[0]), int(p[1])
        out.write(struct.pack('<QI', a, b))
        pos, left = a, b
        while left > 0:
            want = min(left, 4 << 20)
            try:
                c = os.pread(dev, want, pos)
            except OSError:
                c = b''
            if not c:
                out.write(b'\x00' * left)
                bad += left
                left = 0
                break
            out.write(c)
            pos += len(c)
            left -= len(c)
        total += b
out.flush()
sys.stderr.write('sent %d bytes, zero-filled %d\n' % (total, bad))
