#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""列出指定目录下所有 0x24 文件的 path 与原始长度 N（只读）。"""
import os, sys, struct, base64

root = base64.b64decode(sys.argv[1]).decode('utf-8')
NOATIME = 0o40000
out = sys.stdout
out.reconfigure(encoding='utf-8') if hasattr(out, 'reconfigure') else None

for dirpath, dirnames, filenames in os.walk(root):
    dirnames.sort()
    for name in sorted(filenames):
        if not name.endswith('.L0CK3D'):
            continue
        p = os.path.join(dirpath, name)
        try:
            sz = os.path.getsize(p)
            if sz < 588:
                continue
            fd = os.open(p, os.O_RDONLY | NOATIME)
            try:
                t = os.pread(fd, 588, sz - 588)
            finally:
                os.close(fd)
            if t[572] != 0x24:
                continue
            N = struct.unpack('<Q', t[580:588])[0]
            rel = os.path.relpath(p, root).replace(os.sep, '/')
            out.write('%s\t%d\n' % (rel, N))
        except OSError:
            continue
