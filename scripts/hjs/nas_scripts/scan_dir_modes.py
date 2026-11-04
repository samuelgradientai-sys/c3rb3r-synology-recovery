#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""扫描目录内所有 .L0CK3D，解析 588 字节尾部结构，按模式统计。只读本地文件。"""
import os, sys, json, struct, hashlib

def parse(path):
    with open(path, 'rb') as f:
        size = os.fstat(f.fileno()).st_size
        if size < 588:
            return {'file': os.path.basename(path), 'size': size, 'error': 'too small'}
        f.seek(-588, os.SEEK_END)
        tail = f.read(588)
    body_len = size - 588
    magic = tail[568:572]
    mode = tail[572:576]
    aux = struct.unpack('<I', tail[576:580])[0]
    N = struct.unpack('<Q', tail[580:588])[0]
    nonzero_tail = sum(1 for b in tail[:568] if b)
    return {
        'file': os.path.basename(path),
        'size': size,
        'body_len': body_len,
        'magic': magic.hex(),
        'mode': mode.hex(),
        'aux_u32le': aux,
        'N': N,
        'N_ok': (N + 588 == size),
        'tail_nonzero_bytes': nonzero_tail,
        'sha256': hashlib.sha256(open(path,'rb').read()).hexdigest()[:16],
    }

root = sys.argv[1]
rows = []
for name in sorted(os.listdir(root)):
    if name.endswith('.L0CK3D'):
        rows.append(parse(os.path.join(root, name)))

from collections import Counter
c = Counter(r.get('mode') for r in rows)
print(json.dumps({'count': len(rows), 'by_mode': c, 'files': rows}, indent=1, ensure_ascii=False))
