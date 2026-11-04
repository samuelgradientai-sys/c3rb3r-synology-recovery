#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""修复进度（简洁版）：只统计本次重跑，数字直接来自 r_* 日志。"""
import os, time, datetime, subprocess, glob

OUT = r'C:\Users\hjs78\Desktop\修复进度_旧根方案.txt'
LOGD = r'D:\WORK\日志'
E_ROOT = r'E:\恢复数据_Photos'
TOTAL = 2097          # 去重后的失败文件总数
BASE_FILES = 244      # bookend 之前 E 盘的文件数
START = time.mktime(time.strptime('2026-10-30 23:05:00', '%Y-%m-%d %H:%M:%S'))


def lines(path):
    try:
        return open(path, encoding='utf-8', errors='ignore').read().splitlines()
    except OSError:
        return []


def e_count():
    n = 0
    for dp, dn, fn in os.walk(E_ROOT):
        n += len(fn)
    return n


while True:
    ok = bad = skip = 0
    recent = []
    for p in sorted(glob.glob(os.path.join(LOGD, 'r_*_prog.txt'))):
        for ln in lines(p):
            if 'BOOKEND-OK' in ln:
                ok += 1
                recent.append(ln)
            elif 'BOOKEND-BAD' in ln:
                bad += 1
    for p in glob.glob(os.path.join(LOGD, 'r_*_fail.tsv')):
        skip += len(lines(p))
    done = ok + bad + skip
    pct = min(100.0, done * 100.0 / TOTAL)
    fill = int(pct / 2.5)
    bar = '#' * fill + '-' * (40 - fill)
    el = int(time.time() - START)
    h, m = el // 3600, el % 3600 // 60
    rate = done / (el / 60.0) if el > 120 else 0
    eta = int((TOTAL - done) / rate) if rate > 0.1 else 0
    nfiles = e_count()
    el2 = [ln for ln in recent[-3:]]

    txt = []
    txt.append('C3RB3R 修复进度（旧根方案 · 清晰版）')
    txt.append('更新时间：%s' % datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
    txt.append('')
    txt.append('本次任务：把之前失败的 %d 个文件，用“攻击前旧根”方案再试一遍' % TOTAL)
    txt.append('')
    txt.append('  已处理    %5d / %d      （%.1f%%）' % (done, TOTAL, pct))
    txt.append('  成功恢复  %5d 个' % ok)
    txt.append('  无法恢复  %5d 个   （旧数据块已被覆盖，找不到原始内容）' % skip)
    txt.append('  解码失败  %5d 个   （还原出来了但 ffmpeg/图片解码不过，已删除）' % bad)
    txt.append('')
    txt.append('  [%s] %.1f%%' % (bar, pct))
    txt.append('')
    if rate > 0.1:
        txt.append('  处理速度 %.1f 个/分钟，预计还需 %d 分钟' % (rate, eta))
    txt.append('  已运行 %d 小时 %d 分钟' % (h, m))
    txt.append('')
    txt.append('本次已写入磁盘：%d 个文件（E:\\恢复数据_Photos 总数 %d，开工前 %d）'
               % (max(0, nfiles - BASE_FILES), nfiles, BASE_FILES))
    txt.append('')
    txt.append('最近恢复成功：')
    for ln in el2:
        txt.append('  ' + ln)
    txt.append('')
    txt.append('说明：')
    txt.append('  1. 每个文件都用 ffmpeg / Pillow 做完整解码校验，失败即删除并记录。')
    txt.append('  2. 全程只读 NAS，不写入、不删除、不整理。')
    txt.append('  3. 之前已恢复：A 类 22,314 + B 类 410 + C 类 68,459（约 436 GB）。')
    txt.append('  4. 最终数字以磁盘实际文件为准，不用日志行数。')
    try:
        open(OUT + '.tmp', 'w', encoding='utf-8').write('\n'.join(txt))
        os.replace(OUT + '.tmp', OUT)
    except OSError:
        pass
    time.sleep(60)
