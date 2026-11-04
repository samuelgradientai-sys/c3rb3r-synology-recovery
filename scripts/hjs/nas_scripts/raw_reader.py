import sys, os, struct
dev = os.open('/dev/mapper/cachedev_0', os.O_RDONLY)
out = sys.stdout.buffer
total = 0
with open('/tmp/_dsh_ranges.txt') as f:
    for line in f:
        p = line.split()
        if len(p) != 2:
            continue
        a, b = int(p[0]), int(p[1])
        out.write(struct.pack('<QI', a, b))
        pos, left = a, b
        while left > 0:
            c = os.pread(dev, min(left, 4 << 20), pos)
            if not c:
                break
            out.write(c)
            pos += len(c)
            left -= len(c)
        total += b
out.flush()
sys.stderr.write('sent %d bytes\n' % total)
