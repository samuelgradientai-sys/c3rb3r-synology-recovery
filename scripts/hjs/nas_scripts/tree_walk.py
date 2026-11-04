#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""从指定旧 fs tree 根下降到某个 inode，打印它的 EXTENT_DATA（只读）。"""
import subprocess, sys, re

DEV = '/dev/mapper/cachedev_0'
root_bytenr = int(sys.argv[1])
level = int(sys.argv[2])
inode = int(sys.argv[3])

PTR = re.compile(r'key \((\d+) (\w+) (\d+)\) block (\d+)')
ITEM = re.compile(r'item \d+ key \((\d+) (\w+) (\d+)\) itemoff (\d+) itemsize (\d+)')
DISK = re.compile(r'extent data disk byte (\d+) nr (\d+)')
OFF = re.compile(r'extent data offset (\d+) nr (\d+) ram (\d+)')


def dump(b):
    out = subprocess.check_output(['btrfs-debug-tree', '-b', str(b), DEV],
                                  stderr=subprocess.DEVNULL).decode('utf-8', 'ignore')
    return out.splitlines()


cur = root_bytenr
for depth in range(level + 1):
    lines = dump(cur)
    head = None
    for l in lines:
        if l.startswith(('node ', 'leaf ')):
            head = l
            break
    if head is None:
        sys.exit('bad block %d' % cur)
    if head.startswith('node '):
        ptrs = []
        for ln in lines:
            m = PTR.search(ln)
            if m:
                ptrs.append((int(m.group(1)), m.group(2), int(m.group(3)), int(m.group(4))))
        if not ptrs:
            sys.exit('no pointers in %d' % cur)
        pick = ptrs[0][3]
        for o, t, f, b in ptrs:
            if o <= inode:
                pick = b
            else:
                break
        cur = pick
        continue
    # leaf
    items = []
    cur_item = None
    for ln in lines:
        m = ITEM.search(ln)
        if m:
            cur_item = {'obj': int(m.group(1)), 'type': m.group(2), 'off': int(m.group(3)), 'data': []}
            items.append(cur_item)
            continue
        if cur_item is not None:
            cur_item['data'].append(ln.strip())
    res = []
    for it in items:
        if it['obj'] == inode and it['type'] == 'EXTENT_DATA':
            d = '\n'.join(it['data'])
            md = DISK.search(d)
            mo = OFF.search(d)
            res.append((it['off'], int(md.group(1)) if md else None, int(md.group(2)) if md else None,
                        int(mo.group(1)) if mo else None, int(mo.group(2)) if mo else None, d))
    for off, disk, dnr, doff, nbytes, d in res:
        print('RESULT\t%d\t%s\t%s\t%s\t%s' % (off, disk, dnr, doff, nbytes))
    if not res:
        # 打印该叶子覆盖的 inode 范围，便于判断
        objs = sorted(set(it['obj'] for it in items))
        print('NO_EXTENT_DATA inode=%d leaf_objs=%s..%s' % (inode, objs[0] if objs else '-', objs[-1] if objs else '-'))
    break

