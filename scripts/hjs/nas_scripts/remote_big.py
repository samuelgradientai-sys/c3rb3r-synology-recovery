#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""NAS 端只读：大文件(>128MiB) 0x25 逐段还原，流式输出。

帧:
  BIG1 <u16 plen> <path> <u64 size>      后跟 size 字节数据
  SKP1 <u16 plen> <path> <u16 rlen> <reason>
  END1
"""
import os, sys, struct, fcntl, array, bisect, subprocess, re, base64

DEV = '/dev/mapper/cachedev_0'
FOOT = 588
PF = {10: 4, 15: 5, 20: 7, 25: 9, 30: 10, 35: 12, 40: 14, 50: 10, 60: 20, 70: 23, 80: 27}
NOATIME = 0o40000

root = base64.b64decode(sys.argv[1]).decode('utf-8')
max_files = int(sys.argv[2]) if len(sys.argv) > 2 else 0
minsz = int(sys.argv[3]) if len(sys.argv) > 3 else 128 * 1024 * 1024
shard_k = int(sys.argv[4]) if len(sys.argv) > 4 else 0
shard_n = int(sys.argv[5]) if len(sys.argv) > 5 else 1
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
            raise ValueError('logical below chunks')
        c = chunks[i]
        if pos >= c['end']:
            i += 1
            if i >= len(chunks):
                raise ValueError('logical beyond chunks')
            c = chunks[i]
        take = min(left, c['end'] - pos)
        phys = c['phys'] + (pos - c['l'])
        got = os.pread(devfd, take, phys)
        if len(got) != take:
            raise ValueError('short pread')
        buf += got; pos += take; left -= take
    return bytes(buf)


def fiemap_fd(fd):
    CNT = 8192
    hdr = struct.pack('<QQIIII', 0, 0xFFFFFFFFFFFFFFFF, 0, 0, CNT, 0)
    arg = array.array('B', bytearray(hdr) + bytearray(56 * CNT))
    fcntl.ioctl(fd, 0xC020660B, arg, True)
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


stats = {'rec': 0, 'skip': 0, 'bytes': 0, 'seen': 0}
for dirpath, dirnames, filenames in os.walk(root):
    dirnames.sort()
    for name in sorted(filenames):
        if max_files and stats['seen'] >= max_files:
            break
        if not name.endswith('.L0CK3D'):
            continue
        stats['idx'] = stats.get('idx', 0) + 1
        if shard_n > 1 and (stats['idx'] % shard_n) != shard_k:
            continue
        p = os.path.join(dirpath, name)
        rel = os.path.relpath(p, root).replace(os.sep, '/')
        try:
            sz = os.path.getsize(p)
        except OSError:
            continue
        if sz < minsz:
            continue
        stats['seen'] += 1
        fd = None
        try:
            fd = os.open(p, os.O_RDONLY | NOATIME)
            t = os.pread(fd, FOOT, sz - FOOT)
            mode, pct = t[572], t[573]
            N = struct.unpack('<Q', t[580:588])[0]
            if N + FOOT != sz or mode != 0x25:
                emit_skip(rel, 'mode%02x' % mode); stats['skip'] += 1; continue

            ex = fiemap_fd(fd)
            sg = [(s, s + ln) for s, ln in segs(N, mode, pct)]
            cands = sorted(set(ph - lo for lo, ph, ln in ex
                               if not any(not (lo + ln <= s or lo >= e) for s, e in sg)))
            # 文件头签名（用于校验第一段）
            ext = name[:-len('.L0CK3D')].rsplit('.', 1)[-1].lower() if '.' in name[:-len('.L0CK3D')] else ''
            def sig_ok(prefix):
                if ext in ('mp4', 'mov', 'm4v', 'heic'):
                    return prefix[4:8] == b'ftyp'
                if ext in ('jpg', 'jpeg'):
                    return prefix[:3] == b'\xff\xd8\xff'
                if ext == 'png':
                    return prefix[:4] == b'\x89PNG'
                return True
            plan = []
            ok = True
            for si, (s, e) in enumerate(sg):
                a = (s // 4096) * 4096
                b = min(N, ((e + 4095) // 4096) * 4096)
                hit = None
                for d in cands:
                    try:
                        if si == 0 and s == 0 and not sig_ok(pread_logical(d, 16)):
                            continue
                    except Exception:
                        continue
                    good = True
                    try:
                        if s > a and pread_logical(d + a, s - a) != os.pread(fd, s - a, a):
                            good = False
                        if good and b > e and pread_logical(d + e, b - e) != os.pread(fd, b - e, e):
                            good = False
                    except Exception:
                        good = False
                    if good:
                        hit = d; break
                if hit is None:
                    ok = False; break
                plan.append((s, e, hit))
            if not ok:
                emit_skip(rel, 'no-match'); stats['skip'] += 1; continue

            rb = rel.encode('utf-8')
            out.write(b'BIG1' + struct.pack('<H', len(rb)) + rb + struct.pack('<Q', N))
            # 按顺序输出：明文区从文件读，加密段从旧 extent 读
            pos = 0
            CH = 4 << 20
            for s, e, d in plan:
                while pos < s:
                    n = min(CH, s - pos)
                    out.write(os.pread(fd, n, pos))
                    pos += n
                left = e - s
                q = s
                while left > 0:
                    n = min(CH, left)
                    out.write(pread_logical(d + q, n))
                    q += n; left -= n
                pos = e
            while pos < N:
                n = min(CH, N - pos)
                out.write(os.pread(fd, n, pos))
                pos += n
            out.flush()
            stats['rec'] += 1
            stats['bytes'] += N
        except Exception as ex2:
            emit_skip(rel, 'err:%s' % str(ex2)[:40])
            stats['skip'] += 1
        finally:
            if fd is not None:
                os.close(fd)
    if max_files and stats['seen'] >= max_files:
        break

out.write(b'END1')
out.flush()
sys.stderr.write(str(stats) + '\n')
