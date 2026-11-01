# HDMI colour-bar test on the ALIENTEK PYNQ base overlay (no camera)
import sys
import time
import numpy as np
from pynq.overlays.base import BaseOverlay
from pynq.lib.video import VideoMode, PIXEL_RGB

w, h = (int(sys.argv[1]), int(sys.argv[2])) if len(sys.argv) > 2 else (1280, 720)
print("loading overlay", flush=True)
base = BaseOverlay("base.bit")
hdmi_out = base.video.hdmi_out
hdmi_out.configure(VideoMode(w, h, 24), PIXEL_RGB)
hdmi_out.start()

# white, yellow, cyan, green, magenta, red, blue, black
bars = [(255, 255, 255), (255, 255, 0), (0, 255, 255), (0, 255, 0),
        (255, 0, 255), (255, 0, 0), (0, 0, 255), (0, 0, 0)]
frame = hdmi_out.newframe()
for i, c in enumerate(bars):
    frame[:, i * w // 8:(i + 1) * w // 8, :] = c
hdmi_out.writeframe(frame)
print("COLORBAR %dx%d" % (w, h), flush=True)

while True:
    time.sleep(1)
