# Zynq-7020 软硬件协同实时边缘目标检测

基于正点原子领航者 ZYNQ-7020 开发板：OV5640 摄像头采集 → PL 视频流水线（VDMA + HLS 预处理）→ PS 端 YOLO-Fastest 推理 → HDMI 实时显示检测框与帧率。

**关键词**：Zynq 软硬件协同 · HLS 硬件加速 · 边缘目标检测

## 系统架构

```
OV5640 ─DVP─► [PL] SCCB硬件配置 + cmos_capture ─► VDMA ─► DDR3 ◄─ VDMA ─► VTC/rgb2dvi ─► HDMI
                                                          ▲
                           [PL] AXI DMA ─► resize_accel(HLS) ─► AXI DMA (HP1)
                                                          ▲ AXI GP0
[PS] PYNQ Linux：取帧 → 预处理(PL/CPU) → YOLO-Fastest(cv2.dnn) → NMS → 画框/FPS → HDMI
```

| 部分 | 运行位置 | 文件 |
|---|---|---|
| OV5640 上电寄存器配置（SCCB 状态机） | PL | `hw/rtl/ov5640_hw_cfg.v` 等 |
| 采集 / 帧缓存 / HDMI 输出 | PL | Block Design：`hw/bd/` |
| 图像缩放加速 | PL（HLS） | `hw/hls/resize_1.0` |
| 推理与后处理 | PS | `sw/edge_detect.py` |

## 硬件连接

| 设备 | 接口 |
|---|---|
| OV5640 模组 | 底板摄像头接口（断电插拔） |
| 显示器 | 底板 HDMI 口（DVI 显示器用 HDMI-DVI 转接） |
| 电脑 | 网线直连 **PS 网口**（电脑 IP 192.168.2.1，板子 192.168.2.99） |
| 串口 | USB_UART（CH340，115200 8N1） |
| 启动 | BOOT_CFG 拨码 1=OFF、2=OFF（SD 卡启动），SD 卡烧录 PYNQ 2.7 镜像 |

## 构建

工具：Vivado 2026.1（工程由正点原子 2020.2 PYNQ base 工程迁移）。

```bash
# 1. 迁移 base 工程（升级 IP、综合实现）
vivado -mode batch -source hw/scripts/rebuild_base.tcl
# 2. edge_v1：PL 配置摄像头，裁掉 iop_arduino MicroBlaze
vivado -mode batch -source hw/scripts/build_edge_v1.tcl
# 3. edge_v2：加入 AXI DMA + resize_accel 预处理加速
vivado -mode batch -source hw/scripts/build_edge_v2.tcl
```

脚本中的路径按本机 `E:/project/fpga/work` 编写，使用前请修改为自己的目录。生成的 `.bit/.hwh` 放到 `overlay/`。

## 运行（板端，root）

```bash
# 模型文件见 model/README.md
sudo python3 sw/edge_detect.py --image test.jpg --cpu        # 静态图，纯 PS
sudo python3 sw/edge_detect.py --image test.jpg --pl         # 静态图，PL 缩放
sudo python3 sw/edge_detect.py --camera --pl --frames 0      # 实时摄像头 → HDMI
```

各阶段耗时写入 `edge_detect.log`，`--pl` / `--cpu` 用于加速对比。

## 性能

| 指标 | 结果 |
|---|---|
| PL 资源（edge_v2） | LUT 28.6%，FF 20.3%，BRAM 16.8%，DSP 7.3%，时序满足 |
| 板上推理（2 线程，ONNX） | 224：309 ms；256：395 ms；320：607 ms |
| 实时检测 FPS（--cpu / --pl） | 待上板实测 |

## 目录

```
hw/rtl        OV5640 SCCB 配置 Verilog
hw/hls        resize_accel HLS IP
hw/bd         Block Design 导出 tcl
hw/constrs    约束
hw/scripts    Vivado 构建脚本
sw/           板端 Python 应用与调试脚本
model/        模型说明（权重不入库）
docs/         技术文档、提交清单
overlay/      生成的 bit/hwh
```

## 致谢与第三方来源

| 内容 | 来源 | 说明 |
|---|---|---|
| OV5640 SCCB 配置模块 `hw/rtl/i2c_dri.v`、`i2c_ov5640_rgb565_cfg.v` | 正点原子领航者 ZYNQ 例程（42_ov5640_udp_pc），http://www.openedv.com | 保留原作者文件头，`ov5640_hw_cfg.v` 为本项目封装 |
| PYNQ base 工程（视频采集、VDMA、HDMI 输出等 IP） | 正点原子领航者 ZYNQ PYNQ 例程（基于 Xilinx PYNQ） | 由 Vivado 2020.2 迁移到 2026.1，并做了裁剪和修改 |
| `hw/hls/resize_1.0`（resize_accel） | PYNQ resizer 示例，https://github.com/Xilinx/PYNQ | 按 PYNQ 的 BSD-3-Clause 许可使用 |
| YOLO-Fastest v1.1 模型与 cfg | https://github.com/dog-qiuqiu/Yolo-Fastest | 权重不入库，请按原仓库的许可获取和使用 |
| COCO 类别名 | https://cocodataset.org | — |

本仓库只包含本项目编写或移植的源码，不包含正点原子资料盘中的原始文档和压缩包。