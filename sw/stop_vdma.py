#!/usr/bin/env python3
"""Emergency stop for the video VDMA (base/edge overlays, VDMA at 0x43000000).

Use after a camera/HDMI program died without closing its overlay: a running VDMA keeps writing
into freed memory and corrupts the system. Needs only the standard library.
usage: sudo python3 -S stop_vdma.py
"""
import mmap
import os
import struct

VDMA_BASE = 0x43000000
MM2S_DMACR, S2MM_DMACR, S2MM_DMASR = 0x00, 0x30, 0x34
RESET = 0x4

fd = os.open("/dev/mem", os.O_RDWR | os.O_SYNC)
m = mmap.mmap(fd, 0x1000, offset=VDMA_BASE)
rd = lambda off: struct.unpack("<I", m[off:off + 4])[0]
wr = lambda off, v: m.__setitem__(slice(off, off + 4), struct.pack("<I", v))
print("before: MM2S_DMACR %08x S2MM_DMACR %08x S2MM_DMASR %08x" % (rd(MM2S_DMACR), rd(S2MM_DMACR), rd(S2MM_DMASR)))
wr(S2MM_DMACR, RESET)
wr(MM2S_DMACR, RESET)
print("after:  MM2S_DMACR %08x S2MM_DMACR %08x" % (rd(MM2S_DMACR), rd(S2MM_DMACR)))
