#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""按大小分层 + 类型 生成恢复统计（文本报告）。"""
import json

orig = {}
for s in ('hjs', 'ljw', 'lsq'):
    orig[s] = json.load(open(r'D:\WORK\日志\sizes_%s.json' % s, encoding='utf-8-sig'))
rec = json.load(open(r'D:\WORK\日志\recovered_sizes.json', encoding='utf-8'))

BUCKETS = [('lt1m', '小于 1 MB'), ('1to128m', '1 – 128 MB'), ('gt128m', '大于 128 MB')]
TYPES = [('image', '图片'), ('video', '视频'), ('other', '其他（索引/侧车文件）')]


def get(d, b, t):
    return d.get('%s|%s' % (b, t), {'count': 0, 'bytes': 0})


def agg(share_list, b, t):
    n = by = 0
    rn = rb = 0
    for s in share_list:
        o = get(orig[s], b, t)
        r = get(rec.get(s, {}), b, t)
        n += o['count']; by += o['bytes']
        rn += r['count']; rb += r['bytes']
    return n, by, rn, rb


L = []
L.append('C3RB3R 恢复统计（按文件大小分层 + 类型）')
L.append('统计口径：原数据量 = NAS 上加密文件的原始大小（读尾部 footer 的 N 字段）；')
L.append('          恢复数据量 = 本地已通过解码校验的文件实际大小；成功率按文件数/字节数分别算。')
L.append('')
ALL = ['hjs', 'ljw', 'lsq']


def table(shares, title):
    L.append('=' * 96)
    L.append(title)
    L.append('=' * 96)
    L.append('%-18s %18s %18s %10s %10s' % ('大小 / 类型', '原数据量', '已恢复', '文件成功率', '字节成功率'))
    L.append('-' * 96)
    tot_n = tot_b = tot_rn = tot_rb = 0
    for b, bl in BUCKETS:
        for t, tl in TYPES:
            n, by, rn, rb = agg(shares, b, t)
            if n == 0:
                continue
            pr = rn * 100.0 / n
            pb = rb * 100.0 / by if by else 0
            L.append('%-18s %7d 个 %7.1f GB  %7d 个 %7.1f GB  %8.1f%% %8.1f%%'
                     % ('%s %s' % (bl, tl), n, by / 1e9, rn, rb / 1e9, pr, pb))
            tot_n += n; tot_b += by; tot_rn += rn; tot_rb += rb
        L.append('-' * 96)
    L.append('%-18s %7d 个 %7.1f GB  %7d 个 %7.1f GB  %8.1f%% %8.1f%%'
             % ('合计', tot_n, tot_b / 1e9, tot_rn, tot_rb / 1e9,
                tot_rn * 100.0 / tot_n, tot_rb * 100.0 / tot_b))
    L.append('')


table(ALL, '一、三个目录合计（hjs + ljw + lsq）')
table(['hjs'], '二、hjs')
table(['ljw'], '三、ljw')
table(['lsq'], '四、lsq')

L.append('=' * 96)
L.append('五、结论')
L.append('=' * 96)
L.append('1. 真正的照片和视频（图片 <1MB 的缩略图除外）：')
n1, b1, r1, rb1 = agg(ALL, '1to128m', 'image')
n2, b2, r2, rb2 = agg(ALL, '1to128m', 'video')
n3, b3, r3, rb3 = agg(ALL, 'gt128m', 'video')
L.append('   1–128MB 图片 %d/%d = %.1f%%（%.1f/%.1f GB）' % (r1, n1, r1 * 100.0 / n1, rb1 / 1e9, b1 / 1e9))
L.append('   1–128MB 视频 %d/%d = %.1f%%（%.1f/%.1f GB）' % (r2, n2, r2 * 100.0 / n2, rb2 / 1e9, b2 / 1e9))
L.append('   >128MB 视频 %d/%d = %.1f%%（%.1f/%.1f GB）' % (r3, n3, r3 * 100.0 / n3, rb3 / 1e9, b3 / 1e9))
L.append('')
L.append('2. 大于 128MB 的视频：文件数救回 %.1f%%，字节只救回 %.1f%%，' % (r3 * 100.0 / n3, rb3 * 100.0 / b3))
L.append('   因为丢的都是体积最大的那几个（单个 3–8 GB），一丢就掉几十 GB。')
L.append('')
L.append('3. 小于 1MB 的图片：%d/%d = %.1f%%，这批基本是 @eaDir 缩略图，' % (
    agg(ALL, 'lt1m', 'image')[2], agg(ALL, 'lt1m', 'image')[0],
    agg(ALL, 'lt1m', 'image')[2] * 100.0 / agg(ALL, 'lt1m', 'image')[0]))
L.append('   不是照片原图，价值最低，也是拉低总成功率的主因。')
L.append('')
L.append('4. “其他”类是小体积的索引文件（SYNOPHOTO_INDEX、db 等），基本无恢复价值。')

open(r'C:\Users\hjs78\Desktop\恢复统计_按大小类型.txt', 'w', encoding='utf-8').write('\n'.join(L))
print('\n'.join(L))
