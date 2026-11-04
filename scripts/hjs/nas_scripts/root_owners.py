#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""对 find-root 找到的每个候选块，读出它的 owner(tree id)/level/gen。"""
import subprocess, sys, re, base64

DEV = '/dev/mapper/cachedev_0'
lines = open('/tmp/_dsh_roots.txt').read().splitlines()
res = []
for ln in lines:
    ln = ln.strip()
    if not ln:
        continue
    bytenr, gen, level = ln.split()
    try:
        out = subprocess.check_output(['btrfs-debug-tree', '-b', bytenr, DEV],
                                      stderr=subprocess.DEVNULL).decode('utf-8', 'ignore')
    except subprocess.CalledProcessError:
        continue
    m = re.match(r'(leaf|node) \d+ items \d+ free space \d+ generation (\d+) owner (\d+)', out)
    if not m:
        continue
    res.append('%s\t%d\t%d\t%d\t%s' % (bytenr, int(m.group(2)), int(m.group(3)), int(level), m.group(1)))
print('\n'.join(res))
