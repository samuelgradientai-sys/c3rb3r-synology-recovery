#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""B 类批量恢复：多盘输出 + ffmpeg 校验 + 失败删除并记录 + 进度文件。

用法: python run_big_multi.py <远端目录> <输出根1,输出根2,...> <失败日志> [max_files] [进度文件]
"""
import os, sys, struct, hashlib, base64, subprocess, time, shutil

PWD = 'YOUR_PASSWORD'
HOST = 'hjs@NAS_IP'
SSH = ['ssh', '-T', '-o', 'StrictHostKeyChecking=no',
       '-o', 'PreferredAuthentications=password', '-o', 'PubkeyAuthentication=no',
       '-p', '22', HOST]
FFMPEG = r'E:\剪映\JianyingPro\10.5.0.13988\ffmpeg.exe'
MINFREE = 15 * 1024 ** 3

remote_root, roots_arg, faillog = sys.argv[1], sys.argv[2], sys.argv[3]
max_files = int(sys.argv[4]) if len(sys.argv) > 4 else 0
PROGRESS = sys.argv[5] if len(sys.argv) > 5 else None
SHARD_K = int(sys.argv[6]) if len(sys.argv) > 6 else 0
SHARD_N = int(sys.argv[7]) if len(sys.argv) > 7 else 1
roots = [r for r in roots_arg.split(',') if r]


def log_progress(msg):
    if not PROGRESS:
        return
    try:
        with open(PROGRESS, 'a', encoding='utf-8') as pf:
            pf.write('[%s] %s\n' % (time.strftime('%m-%d %H:%M:%S'), msg))
    except OSError:
        pass


log_progress('开始处理：%s' % remote_root)

env = dict(os.environ)
env['SSH_ASKPASS'] = os.path.join(os.environ.get('TEMP', r'C:\Windows\Temp'), 'dsh_askpass.exe')
env['SSH_ASKPASS_REQUIRE'] = 'force'
env['DISPLAY'] = 'localhost:0'

HERE = os.path.dirname(os.path.abspath(__file__))
script = open(os.path.join(HERE, 'remote_big.py'), 'rb').read()
TMP = '/tmp/_dsh_big_%d.py' % os.getpid()
up = subprocess.run(SSH + ['cat > %s && wc -c < %s' % (TMP, TMP)],
                    input=script, stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=env)
if up.returncode != 0:
    raise SystemExit('upload failed')

b64 = base64.b64encode(remote_root.encode('utf-8')).decode('ascii')
cmd = "echo '%s' | sudo -S -p '' python3 %s %s %d %d %d %d" % (
    PWD, TMP, b64, max_files, 128 * 1024 * 1024, SHARD_K, SHARD_N)
p = subprocess.Popen(SSH + [cmd], stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=env)

os.makedirs(os.path.dirname(faillog), exist_ok=True)
flog = open(faillog, 'a', encoding='utf-8')


def pick_root():
    """按传入顺序优先（D→E→C→F），选第一个空间足够的盘。"""
    for r in roots:
        try:
            free = shutil.disk_usage(r).free
        except OSError:
            os.makedirs(r, exist_ok=True)
            free = shutil.disk_usage(r).free
        lim = MINFREE * 2 if r.upper().startswith('C:') else MINFREE
        if free > lim:
            return r
    return None


f = p.stdout
n = 0
bad = 0
skip = 0
t0 = time.time()
while True:
    magic = f.read(4)
    if len(magic) < 4 or magic == b'END1':
        break
    if magic == b'BIG1':
        plen = struct.unpack('<H', f.read(2))[0]
        rel = f.read(plen).decode('utf-8')
        size = struct.unpack('<Q', f.read(8))[0]
        root = pick_root()
        if root is None:
            left = size
            while left:
                b = f.read(min(8 << 20, left))
                if not b:
                    break
                left -= len(b)
            flog.write('SKIP\tno-space\t%s\t-\n' % rel)
            flog.flush()
            skip += 1
            log_progress('SKIP 磁盘不足：%s' % rel.split('/')[-1])
            continue
        dst = os.path.join(root, rel[:-len('.L0CK3D')].replace('/', os.sep))
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        h = hashlib.sha256()
        left = size
        with open(dst, 'wb') as o:
            while left:
                b = f.read(min(8 << 20, left))
                if not b:
                    raise SystemExit('short payload')
                o.write(b); h.update(b); left -= len(b)
        ok = True
        low = dst.lower()
        if low.endswith(('.mp4', '.mov', '.m4v', '.mkv', '.avi')):
            r2 = subprocess.run([FFMPEG, '-v', 'error', '-xerror', '-i', dst, '-f', 'null', '-'],
                                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            ok = (r2.returncode == 0)
        elif low.endswith(('.jpg', '.jpeg')):
            try:
                from PIL import Image
                im = Image.open(dst); im.load()
            except Exception:
                ok = False
        if ok:
            n += 1
            print('OK  %s  %.1f MB  %.1f MB/s' % (rel.split('/')[-1], size / 1e6,
                                                  size / 1e6 / max(time.time() - t0, 1)), flush=True)
            log_progress('OK  %s  %.1fMB  成功累计%d' % (rel.split('/')[-1], size / 1e6, n))
        else:
            KEEP = r'E:\_解码失败_ljw'
            keepdst = os.path.join(KEEP, rel.replace('/', os.sep))
            try:
                os.makedirs(os.path.dirname(keepdst), exist_ok=True)
                if os.path.exists(keepdst):
                    os.remove(keepdst)
                shutil.move(dst, keepdst)
            except Exception:
                try:
                    os.remove(dst)
                except OSError:
                    pass
            flog.write('DECODE-FAIL\t%s\t-\n' % rel)
            flog.flush()
            bad += 1
            print('BAD %s (moved to keep)' % rel.split('/')[-1], flush=True)
            log_progress('BAD %s 解码失败已移入保留目录' % rel.split('/')[-1])
    elif magic == b'SKP1':
        plen = struct.unpack('<H', f.read(2))[0]
        rel = f.read(plen).decode('utf-8')
        rlen = struct.unpack('<H', f.read(2))[0]
        reason = f.read(rlen).decode('utf-8')
        flog.write('SKIP\t%s\t%s\t-\n' % (reason, rel))
        flog.flush()
        skip += 1
        print('SKIP', reason, rel.split('/')[-1], flush=True)
        log_progress('SKIP %s %s' % (reason, rel.split('/')[-1]))

p.wait()
print('DONE ok=%d bad=%d skip=%d elapsed=%.0fs' % (n, bad, skip, time.time() - t0))
log_progress('本目录完成：成功 %d，解码失败 %d，跳过 %d，用时 %.0f 分钟'
             % (n, bad, skip, (time.time() - t0) / 60))
print('remote:', p.stderr.read().decode('utf-8', 'ignore')[:300])

