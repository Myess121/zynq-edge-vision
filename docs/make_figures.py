"""Generate the documentation figures (architecture, software flow, resources, performance).

usage: python make_figures.py      -> writes PNGs into ./figures
All numbers are the measured values recorded in 技术文档.md.
"""
import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch

plt.rcParams["font.sans-serif"] = ["Microsoft YaHei", "SimHei"]
plt.rcParams["axes.unicode_minus"] = False
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "figures")
os.makedirs(OUT, exist_ok=True)

PL_FILL, PS_FILL, EXT_FILL, MEM_FILL = "#E3F0FB", "#FDF0E0", "#EEEEEE", "#E8F5E9"
PL_EDGE, PS_EDGE, EXT_EDGE, MEM_EDGE = "#2F6FA8", "#C7782A", "#666666", "#3C8D40"


def box(ax, x, y, w, h, text, fc, ec, fs=11, bold=False):
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.02,rounding_size=0.12",
                                fc=fc, ec=ec, lw=1.6))
    ax.text(x + w / 2, y + h / 2, text, ha="center", va="center", fontsize=fs,
            fontweight="bold" if bold else "normal", linespacing=1.4)


def arrow(ax, x1, y1, x2, y2, text="", color="#333333", fs=9, style="-|>", ls="-", off=(0, 0.12)):
    ax.add_patch(FancyArrowPatch((x1, y1), (x2, y2), arrowstyle=style, mutation_scale=14,
                                 color=color, lw=1.6, linestyle=ls))
    if text:
        ax.text((x1 + x2) / 2 + off[0], (y1 + y2) / 2 + off[1], text, ha="center", va="bottom",
                fontsize=fs, color=color)


def region(ax, x, y, w, h, title, fc, ec):
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.02,rounding_size=0.2",
                                fc=fc, ec=ec, lw=2, alpha=0.55))
    ax.text(x + 0.15, y + h - 0.12, title, ha="left", va="top", fontsize=13, fontweight="bold", color=ec)


def architecture():
    fig, ax = plt.subplots(figsize=(16, 9), dpi=130)
    ax.set_xlim(0, 16); ax.set_ylim(0, 9); ax.axis("off")
    ax.text(8, 8.75, "系统总体架构（Zynq-7020 软硬件协同）", ha="center", va="top", fontsize=18, fontweight="bold")

    region(ax, 2.3, 4.55, 13.4, 3.75, "PL（FPGA 可编程逻辑）", PL_FILL, PL_EDGE)
    region(ax, 2.3, 0.3, 9.4, 3.85, "PS（双核 ARM Cortex-A9，PYNQ Linux）", PS_FILL, PS_EDGE)

    box(ax, 0.2, 6.0, 1.7, 1.2, "OV5640\n摄像头\n(DVP 8bit)", EXT_FILL, EXT_EDGE, 11, True)
    box(ax, 0.2, 4.2, 1.7, 0.9, "HDMI\n显示器", EXT_FILL, EXT_EDGE, 11, True)

    box(ax, 2.6, 6.75, 2.3, 1.0, "SCCB 硬件配置\nov5640_hw_cfg\n(上电自动写~250寄存器)", "white", PL_EDGE, 9)
    box(ax, 2.6, 5.35, 2.3, 1.0, "cmos_capture\nRGB565→RGB888", "white", PL_EDGE, 10)
    box(ax, 5.3, 5.35, 2.3, 1.0, "颜色转换 / 像素打包\n(HLS IP)", "white", PL_EDGE, 10)
    box(ax, 8.0, 5.35, 2.3, 1.0, "AXI VDMA\nS2MM 写 / MM2S 读", "white", PL_EDGE, 10, True)
    box(ax, 10.7, 6.65, 2.4, 1.0, "VTC + 动态时钟\n1280×720@60", "white", PL_EDGE, 10)
    box(ax, 10.7, 5.35, 2.4, 1.0, "颜色转换(BGR→RGB)\nrgb2dvi TMDS 编码", "white", PL_EDGE, 10)
    box(ax, 13.4, 5.35, 2.1, 2.3, "HLS 预处理加速\nresize_accel\n+ AXI DMA (HP1)\n\n(edge_v2 扩展设计)", "white", PL_EDGE, 10)

    box(ax, 12.2, 1.4, 3.4, 1.6, "DDR3 1GB\n三帧缓冲（摄像头）\n帧缓冲（HDMI）", MEM_FILL, MEM_EDGE, 11, True)

    box(ax, 2.6, 2.2, 2.5, 1.1, "显示主进程\n取帧 · 画框 · 叠加 FPS", "white", PS_EDGE, 10, True)
    box(ax, 5.5, 2.2, 2.6, 1.1, "检测进程(独立)\nYOLO-Fastest\nOpenCV DNN / ONNX", "white", PS_EDGE, 10, True)
    box(ax, 8.5, 2.2, 2.9, 1.1, "后处理（检测进程内）\nYOLO 解码 + NMS", "white", PS_EDGE, 10)
    box(ax, 2.6, 0.6, 2.5, 1.0, "看门狗：3 s 无帧\n→ 重载 bitstream 恢复", "white", PS_EDGE, 9)
    box(ax, 5.5, 0.6, 2.6, 1.0, "预处理 cv2.resize\n640×480→256×256", "white", PS_EDGE, 9)
    box(ax, 8.5, 0.6, 2.9, 1.0, "开机自启 systemd\nedge-demo.service", "white", PS_EDGE, 9)

    arrow(ax, 1.9, 6.6, 2.6, 6.0, "像素数据", fs=9, off=(-0.05, 0.1))
    arrow(ax, 2.6, 7.25, 1.9, 6.95, "SCCB", fs=9, off=(0, 0.08))
    arrow(ax, 4.9, 5.85, 5.3, 5.85)
    arrow(ax, 7.6, 5.85, 8.0, 5.85, "AXI-Stream", fs=9)
    arrow(ax, 9.0, 5.35, 12.5, 3.0, "", PL_EDGE)
    ax.text(10.3, 4.3, "HP0 写入", fontsize=9, color=PL_EDGE)
    arrow(ax, 12.9, 3.0, 9.5, 5.35, "", MEM_EDGE)
    ax.text(11.4, 4.45, "HP0 读出", fontsize=9, color=MEM_EDGE)
    arrow(ax, 10.3, 5.85, 10.7, 5.85)
    arrow(ax, 11.9, 6.65, 11.9, 6.35)
    # TMDS: rgb2dvi -> down -> along the bottom of the PL region -> HDMI monitor
    ax.plot([11.3, 11.3, 2.0], [5.35, 4.65, 4.65], color="#555555", lw=1.6)
    arrow(ax, 2.0, 4.65, 1.9, 4.65, "", "#555555")
    ax.text(6.5, 4.7, "TMDS（HDMI 信号）", fontsize=9, color="#555555", ha="center")
    arrow(ax, 14.45, 5.35, 14.45, 3.0, "HP1", PL_EDGE, 9, ls="--", off=(0.3, 0))
    # DDR frame buffers -> display process (routed above the PS boxes)
    ax.plot([12.2, 11.95, 11.95, 3.85], [2.6, 2.6, 3.55, 3.55], color=PS_EDGE, lw=1.6)
    arrow(ax, 3.85, 3.55, 3.85, 3.3, "", PS_EDGE)
    ax.text(8.0, 3.6, "读取摄像头帧 / 写回显示帧（HP0 数据，GP0 控制）", fontsize=9, color=PS_EDGE, ha="center")
    arrow(ax, 5.1, 2.95, 5.5, 2.95, "", PS_EDGE)
    ax.text(5.3, 3.0, "小图", fontsize=8, color=PS_EDGE, ha="center")
    arrow(ax, 5.5, 2.45, 5.1, 2.45, "", PS_EDGE)
    ax.text(5.3, 2.12, "结果", fontsize=8, color=PS_EDGE, ha="center")
    arrow(ax, 8.1, 2.75, 8.5, 2.75)
    ax.text(0.2, 0.05, "PL 负责：摄像头配置与采集、像素格式转换、帧缓存搬运、HDMI 时序与编码、（扩展）图像缩放加速；"
                       "PS 负责：推理调度、后处理、叠加显示、故障自恢复。", fontsize=10, color="#333333")
    fig.savefig(os.path.join(OUT, "fig1_system_architecture.png"), facecolor="white", bbox_inches="tight")
    plt.close(fig)


def software_flow():
    fig, ax = plt.subplots(figsize=(16, 8.5), dpi=130)
    ax.set_xlim(0, 16); ax.set_ylim(0, 8.5); ax.axis("off")
    ax.text(8, 8.3, "软件流程：显示与检测解耦 + 自动恢复", ha="center", va="top", fontsize=18, fontweight="bold")

    region(ax, 0.3, 0.4, 7.6, 7.2, "显示主进程（约 25–30 帧/秒）", PS_FILL, PS_EDGE)
    region(ax, 8.4, 3.2, 7.3, 4.4, "检测进程（独立 Python 进程，约 1.3 次/秒）", PL_FILL, PL_EDGE)
    region(ax, 8.4, 0.4, 7.3, 2.4, "启动与故障恢复", MEM_FILL, MEM_EDGE)

    steps = ["① VDMA 读取最新摄像头帧（640×480）",
             "② 检测进程空闲？是 → cv2.resize 到 256×256 送入队列",
             "③ 非阻塞取回最新检测结果（框、类别、耗时）",
             "④ 在帧上画框、类别、显示/检测 FPS、推理耗时",
             "⑤ 写入 HDMI 帧缓冲（1280×720，居中）"]
    for i, s in enumerate(steps):
        y = 6.35 - i * 1.15
        box(ax, 0.6, y, 7.0, 0.8, s, "white", PS_EDGE, 11)
        if i < len(steps) - 1:
            arrow(ax, 4.1, y, 4.1, y - 0.35)
    ax.annotate("", xy=(0.45, 6.75), xytext=(0.45, 1.75),
                arrowprops=dict(arrowstyle="-|>", color=PS_EDGE, lw=1.6, connectionstyle="arc3,rad=0"))
    ax.text(0.37, 4.2, "循环", rotation=90, fontsize=10, color=PS_EDGE, ha="right", va="center")

    det = ["从队列取 256×256 RGB 小图", "OpenCV DNN 推理（ONNX，分组卷积）", "YOLO 头解码 + NMS（阈值 0.35 / 0.45）", "结果放回队列"]
    for i, s in enumerate(det):
        y = 6.3 - i * 0.78
        box(ax, 8.8, y, 6.5, 0.6, s, "white", PL_EDGE, 11)
        if i < len(det) - 1:
            arrow(ax, 12.05, y, 12.05, y - 0.18)
    arrow(ax, 7.6, 5.45, 8.8, 6.6, "小图（队列）", "#555555", 9, off=(-0.2, 0.05))
    arrow(ax, 8.8, 4.25, 7.6, 4.55, "检测结果", "#555555", 9, off=(0, -0.45))

    box(ax, 8.8, 1.55, 6.5, 0.85, "看门狗：3 s 无新帧（排线晃动等）→ 关闭 VDMA →\n重新加载 bitstream 并重配摄像头，未恢复则每 2 s 重试", "white", MEM_EDGE, 10)
    box(ax, 8.8, 0.6, 6.5, 0.75, "systemd 开机自启；程序异常 5 s 后自动重启；\n退出时先停 VDMA 再释放缓冲（防止内存被写坏）", "white", MEM_EDGE, 10)
    fig.savefig(os.path.join(OUT, "fig2_software_flow.png"), facecolor="white", bbox_inches="tight")
    plt.close(fig)


def resources():
    designs = ["base（原厂迁移）", "edge_v1（演示版）", "edge_v2（+HLS 缩放）"]
    data = {"LUT": [30.5, 19.7, 28.6], "FF": [20.5, 14.1, 20.3], "BRAM": [7.5, 6.1, 16.8], "DSP": [0.0, 0.0, 7.3]}
    wns = ["-0.267 ns（未满足）", "+0.005 ns（满足）", "+0.003 ns（满足）"]
    fig, ax = plt.subplots(figsize=(14, 7), dpi=130)
    w = 0.2
    colors = ["#2F6FA8", "#6FA8DC", "#C7782A", "#3C8D40"]
    for i, (k, v) in enumerate(data.items()):
        xs = [j + (i - 1.5) * w for j in range(3)]
        bars = ax.bar(xs, v, w, label=k, color=colors[i])
        for x, val in zip(xs, v):
            ax.text(x, val + 0.6, "%.1f%%" % val, ha="center", fontsize=9)
    ax.set_xticks(range(3))
    ax.set_xticklabels(["%s\nWNS %s" % (d, t) for d, t in zip(designs, wns)], fontsize=11)
    ax.set_ylabel("XC7Z020 资源占用 (%)", fontsize=12)
    ax.set_ylim(0, 40)
    ax.set_title("PL 资源占用与时序（Vivado 2026.1 实现结果）", fontsize=16, fontweight="bold")
    ax.legend(fontsize=11, ncol=4, loc="upper right")
    ax.grid(axis="y", alpha=0.3)
    ax.spines[["top", "right"]].set_visible(False)
    fig.savefig(os.path.join(OUT, "fig4_resources.png"), facecolor="white", bbox_inches="tight")
    plt.close(fig)


def performance():
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(16, 6.5), dpi=130)
    sizes = ["224×224", "256×256", "320×320"]
    t1, t2 = [543.8, 715.2, 1096.2], [308.9, 394.8, 606.5]
    x = range(3)
    a1.bar([i - 0.18 for i in x], t1, 0.36, label="单线程", color="#6FA8DC")
    a1.bar([i + 0.18 for i in x], t2, 0.36, label="双线程（cv2.setNumThreads(2)）", color="#2F6FA8")
    for i in x:
        a1.text(i - 0.18, t1[i] + 15, "%.0f" % t1[i], ha="center", fontsize=10)
        a1.text(i + 0.18, t2[i] + 15, "%.0f" % t2[i], ha="center", fontsize=10)
    a1.set_xticks(list(x)); a1.set_xticklabels(sizes, fontsize=11)
    a1.set_ylabel("单帧推理耗时 (ms)", fontsize=12)
    a1.set_title("板上 YOLO-Fastest 推理耗时（静态图，ONNX）", fontsize=14, fontweight="bold")
    a1.legend(fontsize=10); a1.grid(axis="y", alpha=0.3); a1.spines[["top", "right"]].set_visible(False)

    labels = ["摄像头→HDMI\n直通", "实时检测\n显示帧率", "实时检测\n检测频率"]
    vals = [25.5, 28.0, 1.3]
    errs = [0.5, 2.0, 0.1]
    bars = a2.bar(labels, vals, yerr=errs, capsize=6, color=["#3C8D40", "#C7782A", "#2F6FA8"])
    for b, v, unit in zip(bars, vals, ["FPS", "FPS", "次/秒"]):
        a2.text(b.get_x() + b.get_width() / 2, v + 2.2, "%s %s" % (v, unit), ha="center", fontsize=11)
    a2.set_ylim(0, 36)
    a2.set_ylabel("帧/秒", fontsize=12)
    a2.set_title("实时运行性能（edge_v1，256×256 输入）", fontsize=14, fontweight="bold")
    a2.grid(axis="y", alpha=0.3); a2.spines[["top", "right"]].set_visible(False)
    fig.savefig(os.path.join(OUT, "fig5_performance.png"), facecolor="white", bbox_inches="tight")
    plt.close(fig)


if __name__ == "__main__":
    architecture()
    software_flow()
    resources()
    performance()
    print("figures written to", OUT)
