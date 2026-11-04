#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""对保留目录里的文件做快速可读性检测，生成清单（不删除任何文件）。"""
import os, subprocess, sys

ROOT = r'E:\_解码失败_待判断'
FFMPEG = r'E:\剪映\JianyingPro\10.5.0.13988\ffmpeg.exe'
OUT = os.path.join(ROOT, '检测结果.txt')

lines = []
ok_n = bad_n = 0
for dp, dn, fn in os.walk(ROOT):
    for f in sorted(fn):
        if f == '检测结果.txt':
            continue
        p = os.path.join(dp, f)
        rel = os.path.relpath(p, ROOT)
        size = os.path.getsize(p)
        low = f.lower()
        res = ''
        if low.endswith(('.mp4', '.mov', '.m4v', '.mkv')):
            r = subprocess.run([FFMPEG, '-v', 'error', '-i', p, '-t', '10', '-f', 'null', '-'],
                               stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
            res = '前10秒可解码' if r.returncode == 0 else '无法解码'
        elif low.endswith(('.jpg', '.jpeg', '.png')):
            try:
                from PIL import Image
                im = Image.open(p); im.load()
                res = '图片可打开'
            except Exception:
                res = '图片损坏'
        else:
            res = '未知类型'
        if res in ('前10秒可解码', '图片可打开'):
            ok_n += 1
        else:
            bad_n += 1
        lines.append('%-14s  %7.1f MB  %s' % (res, size / 1e6, rel))

head = ['保留文件检测结果（共 %d 个，可读 %d，损坏 %d）' % (len(lines), ok_n, bad_n),
        '说明：视频只解码前 10 秒做结构检查，能通过不代表全程无花屏；请自行播放判断。',
        '-' * 90]
open(OUT, 'w', encoding='utf-8').write('\n'.join(head + lines))
print('ok', ok_n, 'bad', bad_n, 'total', len(lines))
