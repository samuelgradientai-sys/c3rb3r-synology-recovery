#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""NAS 端只读批处理 v3：用"填充区字节匹配"选出每段的原 extent delta。

输出帧:
  REC1 <u16 plen> <path> <u64 size> <32B sha256> <payload>
  SKP1 <u16 plen> <path> <u16 rlen> <reason>
  END1
只读 NAS，不写数据。
"""
import os, sys, struct, json, hashlib, fcntl, array, bisect, subprocess, re, base64

DEV = '/dev/mapper/cachedev_0'
FOOT = 588
PF = {10: 4, 15: 5, 20: 7, 25: 9, 30: 10, 35: 12, 40: 14, 50: 10, 60: 20, 70: 23, 80: 27}
MAXSZ = 128 * 1024 * 1024

root = base64.b64decode(sys.argv[1]).decode('utf-8')
max_files = int(sys.argv[2]) if len(sys.argv) > 2 else 0
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
            raise ValueError('logical %d below chunks' % pos)
        c = chunks[i]
        if pos >= c['end']:
            i += 1
            if i >= len(chunks):
                raise ValueError('logical %d beyond chunks' % pos)
            c = chunks[i]
        take = min(left, c['end'] - pos)
        phys = c['phys'] + (pos - c['l'])
        got = os.pread(devfd, take, phys)
        if len(got) != take:
            raise ValueError('short pread at %d' % phys)
        buf += got; pos += take; left -= take
    return bytes(buf)


def fiemap(path):
    fd = os.open(path, os.O_RDONLY)
    CNT = 4096
    hdr = struct.pack('<QQIIII', 0, 0xFFFFFFFFFFFFFFFF, 0, 0, CNT, 0)
    arg = array.array('B', bytearray(hdr) + bytearray(56 * CNT))
    try:
        fcntl.ioctl(fd, 0xC020660B, arg, True)
    finally:
        os.close(fd)
    raw = bytes(arg)
    m = struct.unpack('<I', raw[20:24])[0]
    res = []
    for i in range(m):
        o = 32 + i * 56
        lo, ph, ln = struct.unpack('<QQQ', raw[o:o + 24])
        res.append((lo, ph, ln))
    return res


def segs(N, mode, pct):
    if mode == 0x26:
        return [(0, min(N, 1024 * 1024))]
    ln = (N // 100) * PF.get(pct, 4)
    gap = (N - 3 * ln) // 2
    return [(i * (ln + gap), ln) for i in range(3)]


def emit_skip(rel, reason):
    rb = rel.encode('utf-8'); sb = reason.encode('utf-8')
    out.write(b'SKP1' + struct.pack('<H', len(rb)) + rb + struct.pack('<H', len(sb)) + sb)


def emit_rec(rel, data):
    rb = rel.encode('utf-8'); h = hashlib.sha256(data).digest()
    out.write(b'REC1' + struct.pack('<H', len(rb)) + rb + struct.pack('<Q', len(data)) + h)
    out.write(data)


stats = {'rec': 0, 'skip': 0, 'bytes': 0, 'seen': 0}
for dirpath, dirnames, filenames in os.walk(root):
    dirnames.sort()
    for name in sorted(filenames):
        if max_files and stats['seen'] >= max_files:
            break
        if not name.endswith('.L0CK3D'):
            continue
        stats['seen'] += 1
        p = os.path.join(dirpath, name)
        rel = os.path.relpath(p, root).replace(os.sep, '/')
        try:
            sz = os.path.getsize(p)
            if sz > MAXSZ:
                emit_skip(rel, 'gt128m'); stats['skip'] += 1; continue
            with open(p, 'rb') as f:
                f.seek(-FOOT, 2)
                t = f.read(FOOT)
                mode, pct = t[572], t[573]
                N = struct.unpack('<Q', t[580:588])[0]
            if N + FOOT != sz or mode not in (0x25, 0x26):
                emit_skip(rel, 'mode%02x' % mode); stats['skip'] += 1; continue

            ex = fiemap(p)
            sg = [(s, s + ln) for s, ln in segs(N, mode, pct)]
            cands = sorted(set(ph - lo for lo, ph, ln in ex
                               if not any(not (lo + ln <= s or lo >= e) for s, e in sg)))
            with open(p, 'rb') as f:
                cur = f.read(N)
            data = bytearray(cur)
            ok = True
            for s, e in sg:
                a = (s // 4096) * 4096
                b = min(N, ((e + 4095) // 4096) * 4096)
                hit = None
                for d in cands:
                    good = True
                    if s > a and pread_logical(d + a, s - a) != cur[a:s]:
                        good = False
                    if good and b > e and pread_logical(d + e, b - e) != cur[e:b]:
                        good = False
                    if good:
                        hit = d
                        break
                if hit is None:
                    if len(cands) == 1 and a == s and b == e:
                        hit = cands[0]
                    else:
                        ok = 'no-match'
                        break
                data[s:e] = pread_logical(hit + s, e - s)
            if ok is not True:
                emit_skip(rel, ok)
                stats['skip'] += 1
                continue
            emit_rec(rel, bytes(data))
            stats['rec'] += 1
            stats['bytes'] += len(data)
            out.flush()
        except Exception as ex2:
            emit_skip(rel, 'err:%s' % str(ex2)[:40])
            stats['skip'] += 1
    if max_files and stats['seen'] >= max_files:
        break

out.write(b'END1')
out.flush()
sys.stderr.write(json.dumps(stats) + '\n')
