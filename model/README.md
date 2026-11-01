# 模型

YOLO-Fastest v1.1（COCO 80 类），原始文件来自 https://github.com/dog-qiuqiu/Yolo-Fastest （ModelZoo/yolo-fastest-1.1_coco）。

| 文件 | 说明 |
|---|---|
| `yolo-fastest-1.1.cfg` / `coco.names` | 原始网络定义与类别名 |
| `yolo-fastest-1.1.weights` | 原始权重（不入库，自行下载） |
| `yolo-fastest-1.1-{224,256,320}.onnx` | 由 `darknet2onnx.py` 导出，板端使用 |
| `darknet2onnx.py` | 无第三方依赖的 Darknet→ONNX 转换（BN 折叠，保留分组卷积，YOLO 头解码在 Python 端） |
| `make_cv42_model.py` | 备用方案：生成 OpenCV 4.2 可读的 Darknet 模型（分组卷积展开，速度慢，仅作对照） |

为什么要转换：PYNQ 2.7 自带 OpenCV 4.2.0，其 Darknet 导入器不支持 `[dropout]`，且分组卷积权重读取错位（输出 NaN）。

```bash
python darknet2onnx.py yolo-fastest-1.1.cfg yolo-fastest-1.1.weights yolo-fastest-1.1-256.onnx 256
```

板端把 `coco.names` 和 `.onnx` 放到 `/home/xilinx/edge/model/`。
