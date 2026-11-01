#!/usr/bin/env python3
"""Camera -> HDMI passthrough for the edge_v1/edge_v2 overlays (OV5640 is configured by the PL).

HDMI runs at 1280x720; the 640x480 camera frame is centred. Saves one frame to cam_frame.jpg
and prints frame statistics so the result can be checked without looking at the monitor.
usage: sudo python3 cam_passthrough.py [overlay.bit]
"""
import os
import sys
import time

import numpy as np
from PIL import Image
from pynq import Overlay
from pynq.lib.video import VideoMode, PIXEL_RGB

HERE = os.path.dirname(os.path.abspath(__file__))
bit = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, "..", "overlay", "edge_v1.bit")
OUT_W, OUT_H, CAM_W, CAM_H = 1280, 720, 640, 480

ol = Overlay(bit)
cam, hdmi = ol.video.camera_in, ol.video.hdmi_out
hdmi.configure(VideoMode(OUT_W, OUT_H, 24), PIXEL_RGB)
hdmi.start()
time.sleep(0.5)                      # PL SCCB state machine finishes ~0.1 s after the bitstream loads
cam.configure(VideoMode(CAM_W, CAM_H, 24))
cam.start()
x0, y0 = (OUT_W - CAM_W) // 2, (OUT_H - CAM_H) // 2
print("running, overlay %s" % bit, flush=True)

n, t0 = 0, time.time()
while True:
    frame = cam.readframe()
    out = hdmi.newframe()
    out[:] = 40
    out[y0:y0 + CAM_H, x0:x0 + CAM_W, :] = frame
    hdmi.writeframe(out)
    if n in (10, 100) or n % 600 == 0:
        print("frame %d mean %.1f std %.1f fps %.1f" % (n, frame.mean(), frame.std(),
                                                       n / max(time.time() - t0, 1e-3)), flush=True)
        if n == 10:
            Image.fromarray(np.array(frame)[:, :, ::-1]).save("cam_frame.jpg")
    frame.freebuffer()
    n += 1
