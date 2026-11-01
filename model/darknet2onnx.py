"""Convert YOLO-Fastest (Darknet cfg/weights) to ONNX without any third-party packages.

Why: OpenCV 4.2 (PYNQ 2.7) cannot load this Darknet model correctly (no dropout layer,
grouped-conv weights misread), but its ONNX importer supports grouped Conv. BatchNorm is
folded into the Conv weights; [yolo] layers are left out and decoded in Python
(see sw/edge_detect.py), so the graph outputs the raw head feature maps.

usage: python darknet2onnx.py model.cfg model.weights model.onnx [input_size]
"""
import struct
import sys
import numpy as np


# ------------------------------------------------------------------ minimal protobuf writer
def _varint(n):
    out = bytearray()
    n &= (1 << 64) - 1
    while True:
        b = n & 0x7F
        n >>= 7
        out.append(b | (0x80 if n else 0))
        if not n:
            return bytes(out)


def f_int(field, v):
    return _varint(field << 3) + _varint(v)


def f_bytes(field, b):
    if isinstance(b, str):
        b = b.encode()
    return _varint(field << 3 | 2) + _varint(len(b)) + b


def f_float(field, v):
    return _varint(field << 3 | 5) + struct.pack("<f", v)


def attr_int(name, v):
    return f_bytes(1, name) + f_int(3, v) + f_int(20, 2)


def attr_float(name, v):
    return f_bytes(1, name) + f_float(2, v) + f_int(20, 1)


def attr_ints(name, vs):
    return f_bytes(1, name) + b"".join(f_int(8, v) for v in vs) + f_int(20, 7)


def attr_floats(name, vs):
    return f_bytes(1, name) + b"".join(f_float(7, v) for v in vs) + f_int(20, 6)


def attr_str(name, s):
    return f_bytes(1, name) + f_bytes(4, s) + f_int(20, 3)


def node(op, inputs, outputs, name, attrs=()):
    return (b"".join(f_bytes(1, i) for i in inputs) + b"".join(f_bytes(2, o) for o in outputs)
            + f_bytes(3, name) + f_bytes(4, op) + b"".join(f_bytes(5, a) for a in attrs))


def tensor(name, arr):
    arr = np.ascontiguousarray(arr, np.float32)
    return b"".join(f_int(1, d) for d in arr.shape) + f_int(2, 1) + f_bytes(8, name) + f_bytes(9, arr.tobytes())


def value_info(name, shape):
    dims = b"".join(f_bytes(1, f_int(1, d)) for d in shape)
    ttype = f_int(1, 1) + f_bytes(2, dims)
    return f_bytes(1, name) + f_bytes(2, f_bytes(1, ttype))


# ------------------------------------------------------------------ darknet parsing
def parse_cfg(path):
    blocks = []
    for line in open(path):
        line = line.split("#")[0].strip()
        if not line:
            continue
        if line.startswith("["):
            blocks.append({"type": line[1:-1].strip()})
        else:
            k, v = line.split("=", 1)
            blocks[-1][k.strip()] = v.strip()
    return blocks


def main(cfg, weights, out_path, size=None):
    blocks = parse_cfg(cfg)
    net, layers = blocks[0], blocks[1:]
    W, H, C = int(net["width"]), int(net["height"]), int(net.get("channels", 3))
    if size:
        W = H = int(size)
    raw = open(weights, "rb").read()
    major, minor, _ = np.frombuffer(raw, np.int32, 3)
    data = np.frombuffer(raw[20 if major * 10 + minor >= 2 else 16:], np.float32)
    pos = 0

    nodes, inits, outputs = [], [], []
    names, ch, hw = [], [], []          # per layer: output tensor name, channels, (h, w)
    cur, cin, size = "input", C, (H, W)
    for i, b in enumerate(layers):
        t, nm = b["type"], "l%d" % i
        if t == "convolutional":
            n, k, s = int(b["filters"]), int(b["size"]), int(b.get("stride", 1))
            g = int(b.get("groups", 1))
            p = k // 2 if int(b.get("pad", 0)) else int(b.get("padding", 0))
            bn = int(b.get("batch_normalize", 0))
            bias = data[pos:pos + n]; pos += n
            if bn:
                scale = data[pos:pos + n]; mean = data[pos + n:pos + 2 * n]; var = data[pos + 2 * n:pos + 3 * n]
                pos += 3 * n
            w = data[pos:pos + n * (cin // g) * k * k].reshape(n, cin // g, k, k); pos += w.size
            if bn:  # fold BN: y = scale*(x-mean)/sqrt(var+eps) + bias
                f = scale / np.sqrt(var + 1e-6)
                w = w * f[:, None, None, None]
                bias = bias - mean * f
            inits.append(tensor(nm + "_w", w)); inits.append(tensor(nm + "_b", bias))
            act = b.get("activation", "linear")
            conv_out = nm if act == "linear" else nm + "_c"
            nodes.append(node("Conv", [cur, nm + "_w", nm + "_b"], [conv_out], nm + "_conv",
                              [attr_ints("kernel_shape", [k, k]), attr_ints("strides", [s, s]),
                               attr_ints("pads", [p, p, p, p]), attr_int("group", g),
                               attr_ints("dilations", [1, 1])]))
            if act == "leaky":
                nodes.append(node("LeakyRelu", [conv_out], [nm], nm + "_act", [attr_float("alpha", 0.1)]))
            elif act != "linear":
                raise ValueError("activation %s" % act)
            cur, cin = nm, n
            size = ((size[0] + 2 * p - k) // s + 1, (size[1] + 2 * p - k) // s + 1)
        elif t == "maxpool":
            k, s = int(b["size"]), int(b["stride"])
            pad = int(b.get("padding", k - 1))
            pl, pr = pad // 2, pad - pad // 2
            nodes.append(node("MaxPool", [cur], [nm], nm, [attr_ints("kernel_shape", [k, k]),
                              attr_ints("strides", [s, s]), attr_ints("pads", [pl, pl, pr, pr])]))
            cur = nm
            size = ((size[0] + pad - k) // s + 1, (size[1] + pad - k) // s + 1)
        elif t == "dropout":
            nm = cur                     # identity at inference
        elif t == "shortcut":
            j = int(b["from"]); j = j if j >= 0 else i + j
            nodes.append(node("Add", [cur, names[j]], [nm], nm))
            cur = nm
        elif t == "route":
            idx = [int(x) for x in b["layers"].split(",")]
            idx = [x if x >= 0 else i + x for x in idx]
            if len(idx) == 1:
                nm = names[idx[0]]
            else:
                nodes.append(node("Concat", [names[x] for x in idx], [nm], nm, [attr_int("axis", 1)]))
            cur, cin, size = nm, sum(ch[x] for x in idx), hw[idx[0]]
        elif t == "upsample":
            s = int(b["stride"])
            nodes.append(node("Upsample", [cur], [nm], nm, [attr_str("mode", "nearest"),
                              attr_floats("scales", [1.0, 1.0, float(s), float(s)])]))
            cur, size = nm, (size[0] * s, size[1] * s)
        elif t == "yolo":
            outputs.append((cur, cin, size))
            nm = cur
        else:
            raise ValueError("layer type %s" % t)
        names.append(nm); ch.append(cin); hw.append(size)
    assert pos == data.size, "weights left over: %d" % (data.size - pos)

    graph = (b"".join(f_bytes(1, n) for n in nodes) + f_bytes(2, "yolo_fastest")
             + b"".join(f_bytes(5, t) for t in inits)
             + f_bytes(11, value_info("input", [1, C, H, W]))
             + b"".join(f_bytes(12, value_info(o, [1, c, h, w])) for o, c, (h, w) in outputs))
    model = f_int(1, 6) + f_bytes(2, "darknet2onnx") + f_bytes(7, graph) + f_bytes(8, f_int(2, 9))
    open(out_path, "wb").write(model)
    print("wrote %s: %d nodes, outputs %s" % (out_path, len(nodes), [(o, c, s) for o, c, s in outputs]))


if __name__ == "__main__":
    main(*sys.argv[1:5])
