#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""本机驱动 bookend 恢复：上传脚本+根表+清单，接收流，校验落盘。

用法: python run_bookend.py <清单文件> <输出根> <日志> <失败记录tsv>
"""
import os, sys, struct, hashlib, subprocess, time, shutil

PWD = 'YOUR_PASSWORD'
HOST = 'hjs@NAS_IP'
SSH = ['ssh', '-T', '-o', 'StrictHostKeyChecking=no',
       '-o', 'PreferredAuthentications=password', '-o', 'PubkeyAuthentication=no',
       '-p', '22', HOST]
FFMPEG = r'E:\剪映\JianyingPro\10.5.0.13988\ffmpeg.exe'

listfile, outroot, logpath, faillog = sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4]
PREFIX = sys.argv[5] if len(sys.argv) > 5 else '/volume1/homes/USER/Photos/'

env = dict(os.environ)
env['SSH_ASKPASS'] = os.path.join(os.environ.get('TEMP', r'C:\Windows\Temp'), 'dsh_askpass.exe')
env['SSH_ASKPASS_REQUIRE'] = 'force'
env['DISPLAY'] = 'localhost:0'
HERE = os.path.dirname(os.path.abspath(__file__))

# 每个进程用独立的远端临时文件，避免并行分片互相覆盖清单
TMP_PY = '/tmp/_bk_%d.py' % os.getpid()
TMP_LIST = '/tmp/_bkl_%d.txt' % os.getpid()
TMP_ROOTS = '/tmp/_bkr_%d.json' % os.getpid()

# 上传脚本与数据
for local, remote in [(os.path.join(HERE, 'bookend.py'), TMP_PY),
                      (r'D:\WORK\roots262.json', TMP_ROOTS),
                      (listfile, TMP_LIST)]:
    data = open(local, 'rb').read()
    r = subprocess.run(SSH + ['cat > %s' % remote], input=data,
                       stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=env)
    if r.returncode != 0:
        raise SystemExit('upload %s failed' % remote)

cmd = "echo '%s' | sudo -S -p '' python3 %s %s %s" % (PWD, TMP_PY, TMP_LIST, TMP_ROOTS)
p = subprocess.Popen(SSH + [cmd], stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=env)

os.makedirs(outroot, exist_ok=True)
flog = open(faillog, 'a', encoding='utf-8')
prog = open(logpath, 'a', encoding='utf-8')
n = bad = 0
t0 = time.time()
f = p.stdout
while True:
    magic = f.read(4)
    if len(magic) < 4 or magic == b'END1':
        break
    if magic == b'BIG1':
        plen = struct.unpack('<H', f.read(2))[0]
        path = f.read(plen).decode('utf-8')
        size = struct.unpack('<Q', f.read(8))[0]
        rel = path.replace(PREFIX, '').replace('.L0CK3D', '')
        dst = os.path.join(outroot, rel.replace('/', os.sep))
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        left = size
        with open(dst, 'wb') as o:
            while left:
                b = f.read(min(8 << 20, left))
                if not b:
                    raise SystemExit('short payload')
                o.write(b); left -= len(b)
        ok = True
        low = dst.lower()
        if low.endswith(('.mp4', '.mov', '.m4v')):
            r = subprocess.run([FFMPEG, '-v', 'error', '-xerror', '-i', dst, '-f', 'null', '-'],
                               stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            ok = (r.returncode == 0)
        else:
            try:
                from PIL import Image
                im = Image.open(dst); im.load()
            except Exception:
                ok = False
        if ok:
            n += 1
            prog.write('[%s] BOOKEND-OK %s %.1fMB\n' % (time.strftime('%m-%d %H:%M:%S'),
                                                         os.path.basename(dst), size / 1e6))
        else:
            bad += 1
            try:
                os.remove(dst)
            except OSError:
                pass
            flog.write('BOOKEND-FAIL\t%s\t%s\n' % (path, 'decode'))
            prog.write('[%s] BOOKEND-BAD %s\n' % (time.strftime('%m-%d %H:%M:%S'),
                                                  os.path.basename(dst)))
        prog.flush(); flog.flush()
    elif magic == b'SKP1':
        plen = struct.unpack('<H', f.read(2))[0]
        path = f.read(plen).decode('utf-8')
        rlen = struct.unpack('<H', f.read(2))[0]
        reason = f.read(rlen).decode('utf-8')
        flog.write('BOOKEND-SKIP\t%s\t%s\n' % (path, reason))
        flog.flush()
p.wait()
prog.write('[%s] 本批完成：成功 %d，解码失败 %d\n' % (time.strftime('%m-%d %H:%M:%S'), n, bad))
prog.close(); flog.close()
print('DONE bookend ok=%d bad=%d elapsed=%.0fs' % (n, bad, time.time() - t0))
print('remote:', p.stderr.read().decode('utf-8', 'ignore')[:300])
