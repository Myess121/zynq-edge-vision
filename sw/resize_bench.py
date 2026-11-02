#!/usr/bin/env python3
"""PS (cv2.resize) vs PL (resize_accel + axi_dma) preprocessing benchmark on a 640x480 frame.
usage: sudo python3 resize_bench.py overlay/edge_v2.bit [image]"""
import os
import sys
import time

import cv2
import numpy as np
from pynq import Overlay

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from edge_detect import CpuResize, PlResize

bit = sys.argv[1]
img = cv2.imread(sys.argv[2]) if len(sys.argv) > 2 else None
src = cv2.resize(img, (640, 480))[:, :, ::-1].copy() if img is not None else \
    np.random.randint(0, 255, (480, 640, 3), np.uint8)

ol = Overlay(bit)
cv2.setNumThreads(1)
for size in (224, 256, 320):
    cpu, pl = CpuResize(), PlResize(ol, 640, 480, size)
    res = {}
    for name, fn in (("cpu", cpu), ("pl", pl)):
        fn(src, size)
        wall, proc = [], []
        for _ in range(50):
            t0, c0 = time.perf_counter(), time.process_time()
            out = fn(src, size)
            wall.append(time.perf_counter() - t0)
            proc.append(time.process_time() - c0)
        res[name] = (out, 1e3 * np.median(wall), 1e3 * np.median(proc))
    diff = np.abs(res["cpu"][0].astype(int) - res["pl"][0].astype(int)).mean()
    print("RESIZE 640x480->%d: cpu %.2f ms (cpu time %.2f) | pl %.2f ms (cpu time %.2f) | mean abs diff %.2f"
          % (size, res["cpu"][1], res["cpu"][2], res["pl"][1], res["pl"][2], diff), flush=True)
