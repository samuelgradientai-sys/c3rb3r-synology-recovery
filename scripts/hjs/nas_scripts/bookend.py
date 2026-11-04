#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Bookend 扫描+重建：对失败文件，从旧根取原始 extent，验证头部后流式输出。

输入:
  /tmp/_dsh_failed.txt   每行一个 NAS 绝对路径
  /tmp/_roots262.json    [{fs_bytenr, level, gen}, ...]
输出帧:
  BIG1 <u16 plen> <path> <u64 size> <payload>
  SKP1 <u16 plen> <path> <u16 rlen> <reason>
  END1
只读 NAS。
"""
import os, sys, struct, subprocess, re, json, bisect

DEV = '/dev/mapper/cachedev_0'
PTR = re.compile(r'key \((\d+) (\w+) (\d+)\) block (\d+)')
ITEM = re.compile(r'item \d+ key \((\d+) (\w+) (\d+)\) itemoff (\d+) itemsize (\d+)')
DISK = re.compile(r'extent data disk byte (\d+) nr (\d+)')
OFF = re.compile(r'extent data offset (\d+) nr (\d+) ram (\d+)')
OWNER = re.compile(r'owner (\d+)')
out = sys.stdout.buffer


def build_chunks():
    txt = subprocess.check_output(['btrfs-debug-tree', '-t', '3', DEV],
                                  stderr=subprocess.DEVNULL).decode('utf-8', 'ignore')
    chunks = []
    cur = None
    for line in txt.splitlines():
        m = re.match(r'\s*item \d+ key \(FIRST_CHUNK_TREE CHUNK_ITEM (\d+)\)', line)
        if m:
            cur = {'l': int(m.group(1)), 'len': None, 'phys': None}
            chunks.append(cur); continue
        if cur is None:
            continue
        m = re.search(r'chunk length (\d+)', line)
        if m and cur['len'] is None:
            cur['len'] = int(m.group(1)); continue
        m = re.search(r'stripe 0 devid \d+ offset (\d+)', line)
        if m and cur['phys'] is None:
            cur['phys'] = int(m.group(1))
    chunks = [c for c in chunks if c['len'] and c['phys'] is not None]
    for c in chunks:
        c['end'] = c['l'] + c['len']
    chunks.sort(key=lambda c: c['l'])
    return chunks, [c['l'] for c in chunks]


chunks, cstarts = build_chunks()
devfd = os.open(DEV, os.O_RDONLY)


def pread_logical(logical, length):
    buf = bytearray(); pos = logical; left = length
    while left > 0:
        i = bisect.bisect_right(cstarts, pos) - 1
        if i < 0:
            raise ValueError('below chunks')
        c = chunks[i]
        if pos >= c['end']:
            i += 1
            if i >= len(chunks):
                raise ValueError('beyond chunks')
            c = chunks[i]
        take = min(left, c['end'] - pos)
        phys = c['phys'] + (pos - c['l'])
        got = os.pread(devfd, take, phys)
        if len(got) != take:
            raise ValueError('short pread')
        buf += got; pos += take; left -= take
    return bytes(buf)


_node_cache = {}


def dump(b, cache=False):
    if cache and b in _node_cache:
        return _node_cache[b]
    lines = subprocess.check_output(['btrfs-debug-tree', '-b', str(b), DEV],
                                    stderr=subprocess.DEVNULL).decode('utf-8', 'ignore').splitlines()
    if cache:
        _node_cache[b] = lines
    return lines


def walk(fs_bytenr, level, inode):
    cur = fs_bytenr
    for _ in range(level + 1):
        lines = dump(cur, cache=len(_node_cache) < 5000)
        head = next((l for l in lines if l.startswith(('node ', 'leaf '))), None)
        if not head:
            return None
        om = OWNER.search(head)
        if not om or int(om.group(1)) != 262:
            return None          # 块已被别的树占用
        if head.startswith('node '):
            ptrs = []
            for ln in lines:
                m = PTR.search(ln)
                if m:
                    ptrs.append((int(m.group(1)), int(m.group(4))))
            if not ptrs:
                return None
            pick = ptrs[0][1]
            for o, b in ptrs:
                if o <= inode:
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
                items.append(ci); continue
            if ci is not None:
                ci['data'].append(ln.strip())
        res = []
        for it in items:
            if it['obj'] == inode and it['type'] == 'EXTENT_DATA':
                d = '\n'.join(it['data'])
                md = DISK.search(d); mo = OFF.search(d)
                if md and mo:
                    res.append((it['off'], int(md.group(1)), int(mo.group(1)), int(mo.group(2))))
        return res if res else None
    return None


def kind_of(b):
    if b[4:8] == b'ftyp':
        return 'mp4'
    if b[:3] == b'\xff\xd8\xff':
        return 'jpeg'
    if b[:4] == b'\x89PNG':
        return 'png'
    return None


def emit_skip(path, reason):
    rb = path.encode('utf-8'); sb = reason.encode('utf-8')
    out.write(b'SKP1' + struct.pack('<H', len(rb)) + rb + struct.pack('<H', len(sb)) + sb)


roots = sorted(json.load(open(sys.argv[2] if len(sys.argv) > 2 else '/tmp/_roots262.json')), key=lambda r: -r['gen'])
paths = [l.strip() for l in open(sys.argv[1] if len(sys.argv) > 1 else '/tmp/_dsh_failed.txt', encoding='utf-8') if l.strip()]
stats = {'good': 0, 'skip': 0, 'bytes': 0}

for path in paths:
    try:
        st = os.stat(path)
        inode = st.st_ino
    except OSError:
        emit_skip(path, 'stat-failed'); stats['skip'] += 1; continue
    got = None
    for r in roots:
        try:
            ex = walk(r['fs_bytenr'], r['level'], inode)
        except Exception:
            ex = None
        if not ex:
            continue
        try:
            head = pread_logical(ex[0][1], 32)
        except Exception:
            continue
        k = kind_of(head)
        if k:
            got = (ex, k)
            break
    if not got:
        emit_skip(path, 'no-valid-extent'); stats['skip'] += 1; continue
    ex, k = got
    # 计算总长
    total = max(o + n for o, d, doff, n in ex)
    rb = path.encode('utf-8')
    out.write(b'BIG1' + struct.pack('<H', len(rb)) + rb + struct.pack('<Q', total))
    CH = 4 << 20
    pos = 0
    try:
        for o, disk, doff, n in sorted(ex):
            if o > pos:
                out.write(b'\x00' * (o - pos))
                pos = o
            left = n
            q = disk + doff
            while left > 0:
                c = min(CH, left)
                out.write(pread_logical(q, c))
                q += c; left -= c; pos += c
        if total > pos:
            out.write(b'\x00' * (total - pos))
    except Exception as e:
        out.write(b'\x00')
    out.flush()
    stats['good'] += 1
    stats['bytes'] += total

out.write(b'END1')
out.flush()
sys.stderr.write(json.dumps(stats) + '\n')

