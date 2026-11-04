#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""只读：输出 FIEMAP 区段 + FS_IOC_GETFLAGS，JSON。"""
import sys, os, json, fcntl, struct, array

path = sys.argv[1]
st = os.stat(path)
fd = os.open(path, os.O_RDONLY)
flags = None
try:
    buf = array.array('i', [0])
    try:
        fcntl.ioctl(fd, 0x80086601, buf, True)
        flags = buf[0]
    except OSError:
        pass
    COUNT = 1024
    hdr = struct.pack('<QQIIII', 0, 0xFFFFFFFFFFFFFFFF, 0, 0, COUNT, 0)
    data = bytearray(hdr) + bytearray(56 * COUNT)
    arg = array.array('B', data)
    fcntl.ioctl(fd, 0xC020660B, arg, True)
    raw = bytes(arg)
    mapped = struct.unpack('<I', raw[20:24])[0]
    exts = []
    for i in range(mapped):
        off = 32 + i * 56
        lo, ph, ln = struct.unpack('<QQQ', raw[off:off+24])
        fl = struct.unpack('<I', raw[off+40:off+44])[0]
        exts.append({'logical': lo, 'physical': ph, 'length': ln, 'flags': fl,
                     'delta': ph - lo})
finally:
    os.close(fd)
print(json.dumps({'path': path, 'size': st.st_size, 'inode': st.st_ino,
                  'fs_flags': ('0x%08x' % flags) if flags is not None else None,
                  'nocow': bool(flags is not None and (flags & 0x00800000)),
                  'extents': exts}, indent=1))
