# OV5640 -> HDMI on the ALIENTEK PYNQ base overlay
# HDMI runs at the verified 1280x720 timing; each 640x480 camera frame is copied into the centre.
# Uses register-level AXI IIC writes with timeouts (the stock XIic_Send can spin forever).
import signal
import sys
import time
import numpy as np
from PIL import Image
from pynq import MMIO
from pynq.overlays.base import BaseOverlay
from pynq.lib.ov5640.ov5640_config import ov5640_init_cfg
from pynq.lib.video import VideoMode, PIXEL_RGB

ADDR = 0x3c
OUT_W, OUT_H = 1280, 720


class Timeout(Exception):
    pass


def on_alarm(*_):
    raise Timeout()


signal.signal(signal.SIGALRM, on_alarm)


class Iic:
    def __init__(self, phys_addr):
        self.m = MMIO(phys_addr, 0x200)
        self.reset()

    def reset(self):
        m = self.m
        m.write(0x040, 0xA)       # soft reset
        m.write(0x120, 0x0F)      # RX FIFO depth
        m.write(0x100, 0x02)      # TX FIFO reset
        m.write(0x100, 0x01)      # enable
        m.write(0x020, m.read(0x020))  # clear interrupts

    def _wait(self, cond, timeout=0.05):
        end = time.time() + timeout
        while not cond():
            if time.time() > end:
                return False
        return True

    def _start(self, rw):
        m = self.m
        if not self._wait(lambda: not (m.read(0x104) & 0x04), timeout=10):
            self.reset()
        m.write(0x020, m.read(0x020))
        m.write(0x108, 0x100 | (ADDR << 1) | rw)

    def write(self, data):
        m = self.m
        self._start(0)
        for b in data[:-1]:
            m.write(0x108, b)
        m.write(0x108, 0x200 | data[-1])
        # the sensor may stretch SCL for seconds while its PLL/reset settles: wait, never reset mid-transfer
        ok = self._wait(lambda: (m.read(0x104) & 0x84) == 0x80, timeout=10)
        nack = m.read(0x020) & 0x02
        if not ok or nack:
            self.reset()
            return False
        return True

    def read_reg(self, reg):
        m = self.m
        if not self.write([reg >> 8, reg & 0xff]):
            return None
        while not (m.read(0x104) & 0x40):  # drain stale RX bytes
            m.read(0x10C)
        self._start(1)
        m.write(0x108, 0x200 | 1)  # read 1 byte then stop
        if not self._wait(lambda: not (m.read(0x104) & 0x40), timeout=1):
            self.reset()
            return None
        return m.read(0x10C) & 0xff

    def wr_reg(self, reg, val, retries=5):
        for _ in range(retries):
            if self.write([reg >> 8, reg & 0xff, val]):
                return True
            time.sleep(0.01)
        return False


print("loading overlay", flush=True)
base = BaseOverlay("base.bit")
camera_in = base.video.camera_in
hdmi_out = base.video.hdmi_out
iic = Iic(base.ip_dict['cam_iic']['phys_addr'])

print("chip id", (iic.read_reg(0x300A), iic.read_reg(0x300B)), flush=True)
failed = 0
streak = 0
# Flash LED forced off first (it can sag the camera supply), soft reset skipped (it kills SCCB on this module;
# the sensor is fresh after board power-up). 'noinit': sensor already configured.
flash_off = [(0x3016, 0x02), (0x301c, 0x02), (0x3019, 0x00)]
init_cfg = [] if 'noinit' in sys.argv else flash_off + [rv for rv in ov5640_init_cfg if rv != (0x3008, 0x82)] + flash_off
for i, (reg, val) in enumerate(init_cfg):
    ok = iic.wr_reg(reg, val, retries=1 if reg == 0x3008 else 5)
    if reg in (0x3008, 0x3103, 0x3037):
        time.sleep(0.5)  # let reset / clock switch settle
    if ok:
        streak = 0
        continue
    failed += 1
    streak += 1
    if streak == 1:
        print("first failure at entry %d reg %04x=%02x" % (i, reg, val), flush=True)
    if streak >= 5:
        print("sensor stopped answering, aborting init", flush=True)
        break
print("ov5640 init done, %d/%d writes failed" % (failed, len(ov5640_init_cfg)), flush=True)
# Match the sensor output to the 640x480 capture path (the init table leaves it at 800x480).
# Same registers as OV5640.set_outsize(), written directly (group hold never launched here).
CAM_W, CAM_H, HTS, VTS = 640, 480, 1800, 1000
outsize = [(0x3808, CAM_W >> 8), (0x3809, CAM_W & 0xff), (0x380a, CAM_H >> 8), (0x380b, CAM_H & 0xff),
           (0x380c, HTS >> 8), (0x380d, HTS & 0xff), (0x380e, VTS >> 8), (0x380f, VTS & 0xff)]
if 'outsize' in sys.argv:
    print("outsize writes failed:", sum(not iic.wr_reg(r, v) for r, v in outsize), flush=True)
    time.sleep(0.2)
print("readback 4300=%s 3808..380b=%s" % (
    iic.read_reg(0x4300), [iic.read_reg(r) for r in (0x3808, 0x3809, 0x380A, 0x380B)]), flush=True)

hdmi_out.configure(VideoMode(OUT_W, OUT_H, 24), PIXEL_RGB)
hdmi_out.start()
# the stock init table leaves the sensor at 800x480 RGB565, so capture at that size by default
cam_mode = VideoMode(CAM_W, CAM_H, 24) if 'outsize' in sys.argv else VideoMode(800, 480, 24)
camera_in.configure(cam_mode)
camera_in.start()
cw, ch = camera_in.mode.width, camera_in.mode.height
x0, y0 = (OUT_W - cw) // 2, (OUT_H - ch) // 2
print("camera mode:", camera_in.mode, flush=True)

n = 0
t0 = time.time()
while True:
    signal.alarm(5)
    try:
        frame = camera_in.readframe()
    except Timeout:
        print("camera readframe TIMEOUT (no frames from sensor)", flush=True)
        continue
    finally:
        signal.alarm(0)
    out = hdmi_out.newframe()
    out[:] = 40
    out[y0:y0 + ch, x0:x0 + cw, :] = frame
    hdmi_out.writeframe(out)
    if n in (5, 50) or n % 300 == 0:
        print("frame %d mean %.1f std %.1f fps %.1f" % (
            n, frame.mean(), frame.std(), n / max(time.time() - t0, 1e-3)), flush=True)
        if n == 5:
            Image.fromarray(np.array(frame)[:, :, ::-1]).save("/home/xilinx/cam_frame.jpg")
    frame.freebuffer()
    n += 1
