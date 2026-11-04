#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""NAS 端只读批处理 v4：优先整段读取旧 extent（顺序 I/O），校验后输出。

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
NOATIME = 0o40000

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


def fiemap_fd(fd):
    CNT = 4096
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


def emit_rec(rel, data):
    rb = rel.encode('utf-8'); h = hashlib.sha256(data).digest()
    out.write(b'REC1' + struct.pack('<H', len(rb)) + rb + struct.pack('<Q', len(data)) + h)
    out.write(data)


def verify_samples(fd, orig, N, sg, n=8):
    """在未加密区段抽 n 个 4KB 块，与当前文件比对。"""
    plain = []
    pos = 0
    for s, e in sorted(sg):
        if s > pos:
            plain.append((pos, s))
        pos = max(pos, e)
    if N > pos:
        plain.append((pos, N))
    total = sum(e - s for s, e in plain)
    if total == 0:
        return True
    step = max(1, total // n)
    done = 0
    for s, e in plain:
        x = s
        while x < e and done < n:
            if os.pread(fd, 4096, x) != orig[x:x + 4096]:
                return False
            done += 1
            x += step
    return True


stats = {'rec': 0, 'skip': 0, 'bytes': 0, 'seen': 0, 'fast': 0}
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
        fd = None
        try:
            sz = os.path.getsize(p)
            if sz > MAXSZ:
                emit_skip(rel, 'gt128m'); stats['skip'] += 1; continue
            fd = os.open(p, os.O_RDONLY | NOATIME)
            t = os.pread(fd, FOOT, sz - FOOT)
            mode, pct = t[572], t[573]
            N = struct.unpack('<Q', t[580:588])[0]
            if N + FOOT != sz or mode not in (0x25, 0x26):
                emit_skip(rel, 'mode%02x' % mode); stats['skip'] += 1; continue

            ex = fiemap_fd(fd)
            sg = [(s, s + ln) for s, ln in segs(N, mode, pct)]
            cands = sorted(set(ph - lo for lo, ph, ln in ex
                               if not any(not (lo + ln <= s or lo >= e) for s, e in sg)))

            data = None
            # 快速路径：整文件一个原 extent → 顺序读一次
            if len(cands) == 1:
                d = cands[0]
                orig = pread_logical(d, N)
                good = True
                for s, e in sg:
                    a = (s // 4096) * 4096
                    b = min(N, ((e + 4095) // 4096) * 4096)
                    if s > a and os.pread(fd, s - a, a) != orig[a:s]:
                        good = False; break
                    if b > e and os.pread(fd, b - e, e) != orig[e:b]:
                        good = False; break
                if good and verify_samples(fd, orig, N, sg):
                    data = orig
                    stats['fast'] += 1
            if data is None:
                # 慢路径：逐段用填充区匹配
                cur = os.pread(fd, N, 0)
                buf = bytearray(cur)
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
                            hit = d; break
                    if hit is None:
                        if len(cands) == 1 and a == s and b == e:
                            hit = cands[0]
                        else:
                            ok = 'no-match'; break
                    buf[s:e] = pread_logical(hit + s, e - s)
                if ok is not True:
                    emit_skip(rel, ok); stats['skip'] += 1; continue
                data = bytes(buf)

            emit_rec(rel, data)
            stats['rec'] += 1
            stats['bytes'] += len(data)
            out.flush()
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
sys.stderr.write(json.dumps(stats) + '\n')
