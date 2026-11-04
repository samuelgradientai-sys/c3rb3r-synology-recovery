#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""本机驱动：同 run_bookend，但不做解码校验、不删除，全部保留（供人工判断）。"""
import os, sys, struct, subprocess, time

PWD = 'YOUR_PASSWORD'
HOST = 'hjs@NAS_IP'
SSH = ['ssh', '-T', '-o', 'StrictHostKeyChecking=no',
       '-o', 'PreferredAuthentications=password', '-o', 'PubkeyAuthentication=no',
       '-p', '22', HOST]

listfile, outroot, logpath = sys.argv[1], sys.argv[2], sys.argv[3]

env = dict(os.environ)
env['SSH_ASKPASS'] = os.path.join(os.environ.get('TEMP', r'C:\Windows\Temp'), 'dsh_askpass.exe')
env['SSH_ASKPASS_REQUIRE'] = 'force'
env['DISPLAY'] = 'localhost:0'
HERE = os.path.dirname(os.path.abspath(__file__))

TMP_PY = '/tmp/_bkk_%d.py' % os.getpid()
TMP_LIST = '/tmp/_bklk_%d.txt' % os.getpid()
TMP_ROOTS = '/tmp/_bkr_%d.json' % os.getpid()

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
prog = open(logpath, 'a', encoding='utf-8')
n = 0
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
        rel = path.replace('/volume1/homes/USER/Photos/', '').replace('.L0CK3D', '')
        dst = os.path.join(outroot, rel.replace('/', os.sep))
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        left = size
        with open(dst, 'wb') as o:
            while left:
                b = f.read(min(8 << 20, left))
                if not b:
                    raise SystemExit('short payload')
                o.write(b); left -= len(b)
        n += 1
        prog.write('[%s] KEEP %s %.1fMB\n' % (time.strftime('%m-%d %H:%M:%S'),
                                               os.path.basename(dst), size / 1e6))
        prog.flush()
    elif magic == b'SKP1':
        plen = struct.unpack('<H', f.read(2))[0]
        path = f.read(plen).decode('utf-8')
        rlen = struct.unpack('<H', f.read(2))[0]
        reason = f.read(rlen).decode('utf-8')
        prog.write('[%s] SKIP %s %s\n' % (time.strftime('%m-%d %H:%M:%S'), reason,
                                          path.split('/')[-1]))
        prog.flush()
p.wait()
prog.write('[%s] 完成：保留 %d 个\n' % (time.strftime('%m-%d %H:%M:%S'), n))
prog.close()
print('DONE keep=%d elapsed=%.0fs' % (n, time.time() - t0))
print('remote:', p.stderr.read().decode('utf-8', 'ignore')[:300])
