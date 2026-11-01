# Register-level AXI IIC master for the OV5640 (7-bit address 0x3c), with timeouts
import time
from pynq import MMIO

ADDR = 0x3c


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
