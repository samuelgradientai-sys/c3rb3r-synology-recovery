#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""按大小分层统计加密文件：<1MB / 1-128MB / >128MB，并区分图片/视频/其他。"""
import os, sys, struct, base64, json

root = base64.b64decode(sys.argv[1]).decode('utf-8')
NOATIME = 0o40000
IMG = {'.jpg', '.jpeg', '.png', '.heic', '.gif', '.bmp', '.tif', '.tiff', '.webp', '.dng', '.raw', '.cr2', '.nef', '.arw'}
VID = {'.mp4', '.mov', '.m4v', '.avi', '.mkv', '.3gp', '.wmv', '.flv', '.mts', '.m2ts', '.insv', '.lrv'}

MB = 1024 * 1024
res = {}


def bucket(n):
    if n < 1 * MB:
        return 'lt1m'
    if n <= 128 * MB:
        return '1to128m'
    return 'gt128m'


def cls(ext):
    if ext in IMG:
        return 'image'
    if ext in VID:
        return 'video'
    return 'other'


for dirpath, dirnames, filenames in os.walk(root):
    for name in filenames:
        if not name.endswith('.L0CK3D'):
            continue
        p = os.path.join(dirpath, name)
        try:
            sz = os.path.getsize(p)
            fd = os.open(p, os.O_RDONLY | NOATIME)
            try:
                t = os.pread(fd, 8, sz - 8)
            finally:
                os.close(fd)
            n = struct.unpack('<Q', t)[0]
            if n <= 0 or n > sz:
                n = sz - 588
        except OSError:
            continue
        base = name[:-7]
        ext = os.path.splitext(base)[1].lower()
        k = (bucket(n), cls(ext))
        d = res.setdefault('%s|%s' % k, {'count': 0, 'bytes': 0})
        d['count'] += 1
        d['bytes'] += n

print(json.dumps(res, ensure_ascii=False))
