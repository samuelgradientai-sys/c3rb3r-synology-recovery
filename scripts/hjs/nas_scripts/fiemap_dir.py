#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""只读：目录内所有 .L0CK3D 的 FIEMAP（logical/physical/length/flags）。"""
import sys, os, json, fcntl, struct, array

def fiemap(fd):
    COUNT = 1024
    hdr = struct.pack('<QQIIII', 0, 0xFFFFFFFFFFFFFFFF, 0, 0, COUNT, 0)
    arg = array.array('B', bytearray(hdr) + bytearray(56 * COUNT))
    fcntl.ioctl(fd, 0xC020660B, arg, True)
    raw = bytes(arg)
    mapped = struct.unpack('<I', raw[20:24])[0]
    out = []
    for i in range(mapped):
        off = 32 + i * 56
        lo, ph, ln = struct.unpack('<QQQ', raw[off:off+24])
        fl = struct.unpack('<I', raw[off+40:off+44])[0]
        out.append({'l': lo, 'p': ph, 'len': ln, 'f': fl})
    return out

root = sys.argv[1]
res = []
for name in sorted(os.listdir(root)):
    if not name.endswith('.L0CK3D'):
        continue
    p = os.path.join(root, name)
    fd = os.open(p, os.O_RDONLY)
    try:
        exts = fiemap(fd)
    finally:
        os.close(fd)
    res.append({'name': name, 'size': os.path.getsize(p), 'ext': exts})
print(json.dumps(res, indent=1))
