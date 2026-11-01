# Read VDMA / video IP status without reloading the bitstream
from pynq import Overlay, MMIO

ol = Overlay("/home/xilinx/pynq/overlays/base/base.bit", download=False)
for name, ip in ol.ip_dict.items():
    if any(k in name for k in ("vdma", "vtc", "dynclk", "v_tc", "iic")):
        print(name, hex(ip['phys_addr']), ip['type'])
vdma = [ip for n, ip in ol.ip_dict.items() if 'vdma' in n][0]
m = MMIO(vdma['phys_addr'], 0x100)
print("MM2S_DMACR %08x  MM2S_DMASR %08x" % (m.read(0x00), m.read(0x04)))
print("MM2S HSIZE %d VSIZE %d STRIDE %d" % (m.read(0x54), m.read(0x50), m.read(0x58) & 0xffff))
print("S2MM_DMACR %08x  S2MM_DMASR %08x" % (m.read(0x30), m.read(0x34)))
print("S2MM HSIZE %d VSIZE %d" % (m.read(0xA4), m.read(0xA0)))
