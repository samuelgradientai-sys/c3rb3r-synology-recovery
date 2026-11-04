#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""从失败 CSV 取 B 类 no-match 文件，取 inode 列表。"""
import csv, os, subprocess, sys

CSV = r'C:\Users\hjs78\Desktop\恢复失败记录_Photos.csv'
OUT = r'D:\WORK\failed8.txt'
N = int(sys.argv[1]) if len(sys.argv) > 1 else 8

rows = [r for r in csv.DictReader(open(CSV, encoding='utf-8-sig'))
        if r['类别'].startswith('B 类（no-match')]
paths = [r['NAS 路径'].replace('/homes/hjs', '/volume1/homes/hjs') for r in rows[:N]]

env = dict(os.environ)
env['SSH_ASKPASS'] = os.path.join(env.get('TEMP', r'C:\Windows\Temp'), 'dsh_askpass.exe')
env['SSH_ASKPASS_REQUIRE'] = 'force'
env['DISPLAY'] = 'localhost:0'

script = 'while IFS= read -r p; do stat -c "%i\\t%n" "$p"; done'
out = subprocess.run(['ssh', '-T', '-o', 'StrictHostKeyChecking=no',
                      '-o', 'PreferredAuthentications=password', '-o', 'PubkeyAuthentication=no',
                      '-p', '22', 'hjs@NAS_IP', script],
                     input='\n'.join(paths).encode('utf-8'),
                     stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, env=env)
lines = out.stdout.decode('utf-8', 'ignore').strip().splitlines()
open(OUT, 'w', encoding='utf-8').write('\n'.join(lines))
print(len(lines), 'lines')
for l in lines[:3]:
    print(l)
