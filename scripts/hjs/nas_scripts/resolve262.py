#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""给定若干 root-tree 块地址，解析出 homes(262) 的 fs tree 根（只读）。"""
import subprocess, re, sys, json

DEV = '/dev/mapper/cachedev_0'
PTR = re.compile(r'key \((\d+) (\w+) (\d+)\) block (\d+)')
ITEM = re.compile(r'item \d+ key \((\d+) (\w+) (\d+)\) itemoff (\d+) itemsize (\d+)')
ROOTDATA = re.compile(r'root data bytenr (\d+) level (\d+).*?gen (\d+)')


def dump(b):
    return subprocess.check_output(['btrfs-debug-tree', '-b', str(b), DEV],
                                   stderr=subprocess.DEVNULL).decode('utf-8', 'ignore').splitlines()


def find262(bytenr, depth=3):
    cur = bytenr
    for _ in range(depth):
        lines = dump(cur)
        head = next((l for l in lines if l.startswith(('node ', 'leaf '))), None)
        if not head:
            return None
        if head.startswith('node '):
            ptrs = []
            for ln in lines:
                m = PTR.search(ln)
                if m or (m := re.search(r'key \((\d+) (\w+) (\d+)\) block (\d+)', ln)):
                    ptrs.append((int(m.group(1)), int(m.group(4))))
            if not ptrs:
                return None
            pick = ptrs[0][1]
            for o, b in ptrs:
                if o <= 262:
                    pick = b
                else:
                    break
            cur = pick
            continue
        items = []
        ci = None
        for ln in lines:
            m = ITEM.search(ln)
            if m:
                ci = {'obj': int(m.group(1)), 'type': m.group(2), 'off': int(m.group(3)), 'data': []}
                items.append(ci)
                continue
            if ci is not None:
                ci['data'].append(ln.strip())
        for it in items:
            if it['obj'] == 262 and it['type'] == 'ROOT_ITEM':
                d = '\n'.join(it['data'])
                m = ROOTDATA.search(d)
                if m:
                    return int(m.group(1)), int(m.group(2)), int(m.group(3))
        return None
    return None


cands = [int(x) for x in sys.argv[1:]]
out = []
for c in cands:
    try:
        r = find262(c)
        if r:
            out.append({'root_tree_block': c, 'fs_bytenr': r[0], 'level': r[1], 'gen': r[2]})
            print(c, '->', r)
        else:
            print(c, '-> NOT FOUND')
    except Exception as e:
        print(c, '-> ERR', str(e)[:50])
json.dump(out, open('/tmp/_roots262.json', 'w'))
