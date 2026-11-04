#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""统计各顶层目录里 >128MiB 的 .L0CK3D 数量与字节。"""
import os, sys, json

root = sys.argv[1]
res = {}
for d in sorted(os.listdir(root)):
    p = os.path.join(root, d)
    if not os.path.isdir(p):
        continue
    n = 0
    b = 0
    for dp, dn, fn in os.walk(p):
        for f in fn:
            if not f.endswith('.L0CK3D'):
                continue
            try:
                s = os.stat(os.path.join(dp, f)).st_size
            except OSError:
                continue
            if s > 128 * 1024 * 1024:
                n += 1
                b += s
    if n:
        res[d] = [n, b]
print(json.dumps(res, ensure_ascii=False, indent=1))
