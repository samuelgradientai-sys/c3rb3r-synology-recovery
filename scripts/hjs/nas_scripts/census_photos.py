#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""只读普查：遍历 Photos，读每个 .L0CK3D 尾部 588 字节，按目录/模式统计。"""
import os, sys, json, struct, collections

root = sys.argv[1]
modes = collections.defaultdict(lambda: [0, 0])      # mode -> [count, bytes]
dirs = collections.defaultdict(lambda: collections.defaultdict(lambda: [0, 0]))
others = [0, 0]
errors = 0
n_enc = 0
for dirpath, dirnames, filenames in os.walk(root):
    rel = os.path.relpath(dirpath, root)
    top = '(root)' if rel == '.' else rel.split(os.sep)[0]
    for name in filenames:
        p = os.path.join(dirpath, name)
        if not name.endswith('.L0CK3D'):
            try:
                others[0] += 1
                others[1] += os.path.getsize(p)
            except OSError:
                pass
            continue
        try:
            sz = os.path.getsize(p)
            if sz < 588:
                errors += 1
                continue
            with open(p, 'rb') as f:
                f.seek(-588, os.SEEK_END)
                t = f.read(588)
            mode = t[572]
        except OSError:
            errors += 1
            continue
        k = '%02x' % mode
        modes[k][0] += 1
        modes[k][1] += sz
        dirs[top][k][0] += 1
        dirs[top][k][1] += sz
        n_enc += 1

out = {
    'root': root,
    'encrypted_files': n_enc,
    'encrypted_bytes': sum(v[1] for v in modes.values()),
    'by_mode': {k: {'count': v[0], 'bytes': v[1]} for k, v in sorted(modes.items())},
    'other_files': {'count': others[0], 'bytes': others[1]},
    'errors': errors,
    'by_top_dir': {d: {k: {'count': v[0], 'bytes': v[1]} for k, v in sorted(m.items())}
                   for d, m in sorted(dirs.items())},
}
print(json.dumps(out, indent=1, ensure_ascii=False))
