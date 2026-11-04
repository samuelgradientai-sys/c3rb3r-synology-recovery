#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""鏈満缂栨帓锛氫笂浼犺繙绔彧璇昏剼鏈?-> 杩愯 -> 鎺ユ敹娴?-> 钀界洏 -> 璁板綍澶辫触娓呭崟銆?
鐢ㄦ硶:
  python run_local.py <杩滅鐩綍> <鏈満鏄犲皠鍓嶇紑> <澶辫触鏃ュ織tsv> [max_files]

钀界洏璺緞 = 鏈満鏄犲皠鍓嶇紑 \\ <杩滅鐩稿璺緞鍘绘帀 .L0CK3D>
渚嬪杩滅 /volume1/homes/USER/Photos/缁撳/鍘熺墖/6Z6A6282.JPG.L0CK3D
     鍓嶇紑 F:\\鎭㈠鏁版嵁_Photos\\homes\\hjs\\Photos
  -> F:\\鎭㈠鏁版嵁_Photos\\homes\\hjs\\Photos\\缁撳\\鍘熺墖\\6Z6A6282.JPG
"""
import os, sys, struct, hashlib, base64, subprocess, time

PWD = 'YOUR_PASSWORD'
HOST = 'hjs@NAS_IP'
SSH = ['ssh', '-T', '-o', 'StrictHostKeyChecking=no',
       '-o', 'PreferredAuthentications=password', '-o', 'PubkeyAuthentication=no',
       '-p', '22', HOST]

remote_root, outroot, faillog = sys.argv[1], sys.argv[2], sys.argv[3]
max_files = int(sys.argv[4]) if len(sys.argv) > 4 else 0

env = dict(os.environ)
env['SSH_ASKPASS'] = os.path.join(os.environ.get('TEMP', r'C:\Windows\Temp'), 'dsh_askpass.exe')
env['SSH_ASKPASS_REQUIRE'] = 'force'
env['DISPLAY'] = 'localhost:0'

HERE = os.path.dirname(os.path.abspath(__file__))
script = open(os.path.join(HERE, 'remote_batch_fast.py'), 'rb').read()

# 1) 涓婁紶鑴氭湰锛堝啓鍒?NAS /tmp锛岀敤鍚庡垹闄わ級
up = subprocess.run(SSH + ['cat > /tmp/_dsh_batch2.py && wc -c < /tmp/_dsh_batch2.py'],
                    input=script, stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=env)
if up.returncode != 0:
    raise SystemExit('upload failed: %s' % up.stderr.decode('utf-8', 'ignore'))
print('remote script bytes:', up.stdout.decode().strip(), 'local:', len(script))

b64 = base64.b64encode(remote_root.encode('utf-8')).decode('ascii')
cmd = "echo '%s' | sudo -S -p '' python3 /tmp/_dsh_batch2.py %s %d" % (PWD, b64, max_files)
p = subprocess.Popen(SSH + [cmd], stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=env)

os.makedirs(outroot, exist_ok=True)
os.makedirs(os.path.dirname(faillog), exist_ok=True)
flog = open(faillog, 'a', encoding='utf-8')

nrec = nskip = nbytes = 0
t0 = time.time()
f = p.stdout
while True:
    magic = f.read(4)
    if len(magic) < 4:
        print('stream ended unexpectedly')
        break
    if magic == b'END1':
        break
    if magic == b'REC1':
        plen = struct.unpack('<H', f.read(2))[0]
        rel = f.read(plen).decode('utf-8')
        size = struct.unpack('<Q', f.read(8))[0]
        sha = f.read(32)
        dst = os.path.join(outroot, rel[:-len('.L0CK3D')].replace('/', os.sep))
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        h = hashlib.sha256()
        with open(dst, 'wb') as o:
            left = size
            while left > 0:
                b = f.read(min(1 << 20, left))
                if not b:
                    raise SystemExit('short payload: %s' % rel)
                o.write(b)
                h.update(b)
                left -= len(b)
        if h.digest() != sha:
            flog.write('SHAFAIL\t%s\t-\t%s\n' % (rel, size))
            flog.flush()
        nrec += 1
        nbytes += size
        if nrec % 100 == 0:
            el = time.time() - t0
            print('rec=%d skip=%d %.1f GB  %.1f MB/s' % (nrec, nskip, nbytes / 1e9, nbytes / 1e6 / max(el, 1)))
            sys.stdout.flush()
    elif magic == b'SKP1':
        plen = struct.unpack('<H', f.read(2))[0]
        rel = f.read(plen).decode('utf-8')
        rlen = struct.unpack('<H', f.read(2))[0]
        reason = f.read(rlen).decode('utf-8')
        flog.write('SKIP\t%s\t%s\t-\n' % (reason, rel))
        flog.flush()
        nskip += 1
    else:
        raise SystemExit('bad magic %r' % magic)

p.wait()
err = p.stderr.read().decode('utf-8', 'ignore').strip()
flog.write('SUMMARY\trec=%d\tskip=%d\tbytes=%d\t%s\n' % (nrec, nskip, nbytes, err))
flog.close()
print('DONE rec=%d skip=%d bytes=%.2f GB elapsed=%.0fs' % (nrec, nskip, nbytes / 1e9, time.time() - t0))
print('remote stderr:', err[:500])

