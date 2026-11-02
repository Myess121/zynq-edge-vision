#!/usr/bin/env python3
"""Edge object detection on the Navigator ZYNQ-7020 (PYNQ 2.7).

Pipeline: OV5640 -> VDMA (PL) -> DDR -> preprocess (PL resize_accel or cv2.resize)
          -> YOLO-Fastest via cv2.dnn (PS) -> boxes + FPS overlay -> HDMI frame buffer.

Usage examples (run as root on the board):
  python3 edge_detect.py --image test.jpg --cpu            # static image, PS only
  python3 edge_detect.py --image test.jpg --pl             # static image, PL resize
  python3 edge_detect.py --camera --pl                     # live camera -> HDMI
"""
import argparse
import logging
import multiprocessing as mp
import os
import queue
import signal
import sys
import time

import cv2
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
DEFAULT_OVERLAY = os.path.join(HERE, "..", "overlay", "edge_v1.bit")
DEFAULT_MODEL = os.path.join(HERE, "..", "model")
OUT_W, OUT_H = 1280, 720
CAM_W, CAM_H = 640, 480

log = logging.getLogger("edge")


# ----------------------------------------------------------------------------- model
ANCHORS = np.array([[12, 18], [37, 49], [52, 132], [115, 73], [119, 199], [242, 238]], np.float32)
# head outputs in graph order: the stride-32 head uses anchors 3,4,5, the stride-16 head 0,1,2
HEAD_MASKS = {32: [3, 4, 5], 16: [0, 1, 2]}


def _sigmoid(x):
    return 1.0 / (1.0 + np.exp(-x))


class YoloFastest:
    """YOLO-Fastest on cv2.dnn: ONNX (model/darknet2onnx.py, decoded here) or the Darknet files."""

    def __init__(self, model_dir, size, conf=0.35, nms=0.45, fmt="auto"):
        with open(os.path.join(model_dir, "coco.names")) as f:
            self.names = [l.strip() for l in f if l.strip()]
        onnx = os.path.join(model_dir, "yolo-fastest-1.1-%d.onnx" % size)
        old_cv = tuple(int(x) for x in cv2.__version__.split(".")[:2]) < (4, 5)
        # OpenCV 4.2 (PYNQ 2.7) cannot load this Darknet model correctly (no dropout layer,
        # grouped-conv weights misread), so the ONNX export is used there
        self.onnx = fmt == "onnx" or (fmt == "auto" and (old_cv or os.path.exists(onnx)))
        if self.onnx:
            self.net = cv2.dnn.readNetFromONNX(onnx)
        else:
            self.net = cv2.dnn.readNetFromDarknet(os.path.join(model_dir, "yolo-fastest-1.1.cfg"),
                                                  os.path.join(model_dir, "yolo-fastest-1.1.weights"))
        self.net.setPreferableBackend(cv2.dnn.DNN_BACKEND_OPENCV)
        self.net.setPreferableTarget(cv2.dnn.DNN_TARGET_CPU)
        self.outs = self.net.getUnconnectedOutLayersNames()
        self.size, self.conf, self.nms = size, conf, nms

    def _decode_heads(self, outs):
        """Raw head maps (1, 3*85, h, w) -> rows [cx, cy, w, h, score_per_class...] normalised to 0..1."""
        rows = []
        for o in outs:
            _, _, gh, gw = o.shape
            anchors = ANCHORS[HEAD_MASKS[self.size // gh]]
            p = o.reshape(3, 85, gh, gw).transpose(0, 2, 3, 1)          # (3, gh, gw, 85)
            gy, gx = np.mgrid[0:gh, 0:gw]
            cx = (_sigmoid(p[..., 0]) + gx) / gw
            cy = (_sigmoid(p[..., 1]) + gy) / gh
            w = np.exp(p[..., 2]) * anchors[:, 0, None, None] / self.size
            h = np.exp(p[..., 3]) * anchors[:, 1, None, None] / self.size
            cls = _sigmoid(p[..., 5:]) * _sigmoid(p[..., 4:5])
            rows.append(np.concatenate([np.stack([cx, cy, w, h], -1), cls], -1).reshape(-1, 84))
        return np.concatenate(rows)

    def infer(self, rgb_small, orig_w, orig_h):
        """rgb_small: size x size x 3 uint8 RGB (already resized). Returns [(cls, score, x, y, w, h)]."""
        blob = cv2.dnn.blobFromImage(rgb_small, 1 / 255.0, swapRB=False, crop=False)
        self.net.setInput(blob)
        outs = self.net.forward(self.outs)
        if self.onnx:
            dets = self._decode_heads(outs)
        else:  # OpenCV region layer rows: [cx, cy, w, h, obj, class scores already x obj]
            dets = np.concatenate(outs)
            dets = np.concatenate([dets[:, :4], dets[:, 5:]], 1)
        cls_ids = np.argmax(dets[:, 4:], 1)
        cls_sc = dets[np.arange(len(dets)), 4 + cls_ids]
        keep = np.nonzero(cls_sc >= self.conf)[0]
        boxes, scores, classes = [], [], []
        for i in keep:
            cx, cy, w, h = dets[i, 0] * orig_w, dets[i, 1] * orig_h, dets[i, 2] * orig_w, dets[i, 3] * orig_h
            boxes.append([int(cx - w / 2), int(cy - h / 2), int(w), int(h)])
            scores.append(float(cls_sc[i]))
            classes.append(int(cls_ids[i]))
        keep = cv2.dnn.NMSBoxes(boxes, scores, self.conf, self.nms)
        keep = np.array(keep).flatten() if len(keep) else []
        return [(classes[i], scores[i], *boxes[i]) for i in keep]


# ----------------------------------------------------------------------------- preprocess
class CpuResize:
    name = "cpu"

    def __call__(self, rgb, size):
        return cv2.resize(rgb, (size, size), interpolation=cv2.INTER_LINEAR)


class PlResize:
    """resize_accel HLS IP fed by axi_dma (same register map as the PYNQ resizer example)."""
    name = "pl"

    def __init__(self, ol, src_w, src_h, size):
        from pynq import allocate
        self.dma = ol.axi_dma_0
        self.ip = ol.resize_accel_0
        self.src = allocate(shape=(src_h, src_w, 3), dtype=np.uint8, cacheable=1)
        self.dst = allocate(shape=(size, size, 3), dtype=np.uint8, cacheable=1)
        rm = self.ip.register_map
        rm.src_rows, rm.src_cols, rm.dst_rows, rm.dst_cols = src_h, src_w, size, size

    def __call__(self, rgb, size):
        self.src[:] = rgb
        self.dma.sendchannel.transfer(self.src)
        self.dma.recvchannel.transfer(self.dst)
        self.ip.write(0x00, 0x81)  # ap_start | auto_restart
        self.dma.sendchannel.wait()
        self.dma.recvchannel.wait()
        return np.array(self.dst)


# ----------------------------------------------------------------------------- drawing
def draw(img, dets, names, stats):
    ih, iw = img.shape[:2]
    for c, s, x, y, w, h in dets:
        x, y = max(0, min(int(x), iw - 1)), max(0, min(int(y), ih - 1))
        w, h = max(1, min(int(w), iw - 1 - x)), max(1, min(int(h), ih - 1 - y))
        cv2.rectangle(img, (x, y), (x + w, y + h), (0, 255, 0), 2)
        cv2.putText(img, "%s %.2f" % (names[c] if c < len(names) else c, s), (x, max(12, y - 4)),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1)
    y = 20
    for k, v in stats:
        cv2.putText(img, "%s: %s" % (k, v), (8, y), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (255, 255, 0), 1)
        y += 20
    return img


# ----------------------------------------------------------------------------- main
def run_image(args, model, pre):
    bgr = cv2.imread(args.image)
    if bgr is None:
        sys.exit("cannot read %s" % args.image)
    rgb = cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)
    h, w = rgb.shape[:2]
    times = []
    for i in range(args.frames):
        t0, c0 = time.perf_counter(), time.process_time()
        small = pre(rgb, args.size)
        t1, c1 = time.perf_counter(), time.process_time()
        dets = model.infer(small, w, h)
        t2 = time.perf_counter()
        times.append((t1 - t0, t2 - t1, c1 - c0))
        log.info("frame %d pre=%.1fms infer=%.1fms dets=%d", i, (t1 - t0) * 1e3, (t2 - t1) * 1e3, len(dets))
    pre_ms = 1e3 * np.median([t[0] for t in times])
    inf_ms = 1e3 * np.median([t[1] for t in times])
    stats = [("mode", pre.name), ("input", "%dx%d" % (args.size, args.size)),
             ("pre", "%.1f ms" % pre_ms), ("pre_cpu", "%.1f ms" % (1e3 * np.median([t[2] for t in times]))),
             ("infer", "%.1f ms" % inf_ms),
             ("fps", "%.2f" % (1e3 / (pre_ms + inf_ms)))]
    out = draw(bgr.copy(), dets, model.names, stats)
    cv2.imwrite(args.out, out)
    log.info("RESULT %s", " ".join("%s=%s" % kv for kv in stats))
    for c, s, *_ in dets:
        log.info("  %s %.2f", model.names[c], s)


class CaptureTimeout(Exception):
    pass


def _on_alarm(*_):
    raise CaptureTimeout()


def _on_term(*_):
    raise SystemExit(0)


def run_camera(args, model, pre_factory):
    signal.signal(signal.SIGALRM, _on_alarm)
    # the VDMA must be stopped before its buffers are freed (see the finally below), otherwise it
    # keeps writing into memory the kernel reuses: turn SIGTERM/SIGINT into a normal exit
    signal.signal(signal.SIGTERM, _on_term)
    signal.signal(signal.SIGINT, _on_term)
    from pynq import Overlay
    from pynq.lib.video import VideoMode, PIXEL_RGB
    # spawn (not fork): the worker must not inherit the overlay, DMA buffers or OpenCV thread state
    ctx = mp.get_context("spawn")
    req_q, res_q = ctx.Queue(maxsize=1), ctx.Queue(maxsize=1)
    worker = ctx.Process(target=detector_process, args=(args.model_dir, args.size, args.threads, req_q, res_q),
                         daemon=True)
    worker.start()
    ol = Overlay(args.overlay)

    def open_video():
        c, h = ol.video.camera_in, ol.video.hdmi_out
        h.configure(VideoMode(OUT_W, OUT_H, 24), PIXEL_RGB)
        h.start()
        time.sleep(0.5)                  # PL SCCB state machine configures the sensor after reset
        c.configure(VideoMode(CAM_W, CAM_H, 24))
        c.start()
        return c, h

    cam, hdmi = open_video()
    pre = pre_factory(ol)
    x0, y0 = (OUT_W - CAM_W) // 2, (OUT_H - CAM_H) // 2
    small_buf = np.zeros((args.size, args.size, 3), np.uint8)

    # Display and detection are decoupled: this process keeps camera -> HDMI at full rate and
    # overlays the latest boxes; a separate process (no shared GIL, no pynq) runs inference on the
    # newest preprocessed frame. Only the small network input and the box list cross processes.
    dets, inf_ms, det_fps, pre_ms, busy = [], 0.0, 0.0, 0.0, False
    n, t_start, disp_fps, stalls = 0, time.perf_counter(), 0.0, 0
    try:
        while args.frames <= 0 or n < args.frames:
            t0 = time.perf_counter()
            # a glitch on the camera bus (e.g. the ribbon being moved) can wedge the capture pipeline
            # (VDMA S2MM and the HLS pixel IPs); a VDMA reset alone does not recover it, so reload the
            # bitstream, which also re-runs the PL sensor configuration
            signal.alarm(3)
            try:
                frame = cam.readframe()      # BGR order from the capture pipeline
                stalls = 0
            except (CaptureTimeout, RuntimeError) as e:   # stuck, or the channel halted on an error
                stalls += 1
                log.warning("capture stalled (%s), reloading the overlay (#%d)", e.__class__.__name__, stalls)
                if stalls > 3:
                    raise RuntimeError("capture does not recover")
                cam.close()                      # stop both VDMA channels before freeing buffers
                hdmi.close()
                ol.download()
                cam, hdmi = open_video()
                continue
            finally:
                signal.alarm(0)
            bgr = np.array(frame)
            frame.freebuffer()
            if not busy:                         # hand the newest frame to the detector
                tp = time.perf_counter()
                small_buf[:] = pre(np.ascontiguousarray(bgr[:, :, ::-1]), args.size)
                pre_ms = (time.perf_counter() - tp) * 1e3
                req_q.put(small_buf)
                busy = True
            try:
                dets, inf_ms, det_fps = res_q.get_nowait()
                busy = False
            except queue.Empty:
                pass
            if args.fake_dets and n >= 60:      # debug: draw boxes every frame, incl. off-screen ones
                dets = [(62, 0.9, 200, 120, 240, 200), (0, 0.8, -50, -30, 120, 600), (39, 0.7, 600, 450, 300, 100)]
            view = draw(bgr, dets, model.names,
                        [("mode", pre.name), ("display fps", "%.1f" % disp_fps),
                         ("detect fps", "%.2f" % det_fps), ("pre", "%.1f ms" % pre_ms),
                         ("infer", "%.1f ms" % inf_ms)])
            out = hdmi.newframe()
            out[:] = 0
            out[y0:y0 + CAM_H, x0:x0 + CAM_W, :] = view
            hdmi.writeframe(out)
            if n in (150, 450, 900):
                cv2.imwrite("det_cam_%d.jpg" % n, view)
            dt = time.perf_counter() - t0
            disp_fps = 0.9 * disp_fps + 0.1 / max(dt, 1e-6) if n else 1 / max(dt, 1e-6)
            if n % 30 == 0:
                log.info("frame %d display_fps=%.1f detect_fps=%.2f pre=%.1f infer=%.1f ms dets=%d",
                         n, disp_fps, det_fps, pre_ms, inf_ms, len(dets))
            n += 1
    finally:
        signal.alarm(0)
        cam.close()                              # stop the VDMA before anything else
        hdmi.close()
        worker.terminate()
        log.info("frames=%d avg_display_fps=%.2f", n, n / (time.perf_counter() - t_start))


def detector_process(model_dir, size, threads, req_q, res_q):
    """Inference worker: receives size x size RGB arrays, returns (dets, infer_ms, det_fps)."""
    signal.signal(signal.SIGINT, signal.SIG_IGN)
    cv2.setNumThreads(threads)
    model = YoloFastest(model_dir, size)
    last = time.perf_counter()
    while True:
        small = req_q.get()
        t0 = time.perf_counter()
        dets = model.infer(small, CAM_W, CAM_H)
        t1 = time.perf_counter()
        res_q.put((dets, (t1 - t0) * 1e3, 1.0 / max(t1 - last, 1e-6)))
        last = t1


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    g = ap.add_mutually_exclusive_group()
    g.add_argument("--pl", action="store_true", help="resize in PL (resize_accel + axi_dma)")
    g.add_argument("--cpu", action="store_true", help="resize with cv2 on the ARM cores (default)")
    src = ap.add_mutually_exclusive_group(required=True)
    src.add_argument("--image", help="static test image")
    src.add_argument("--camera", action="store_true", help="live OV5640 -> HDMI")
    ap.add_argument("--overlay", default=DEFAULT_OVERLAY)
    ap.add_argument("--model-dir", default=DEFAULT_MODEL)
    ap.add_argument("--size", type=int, default=256, help="network input size (224/256/320)")
    ap.add_argument("--threads", type=int, default=2, help="OpenCV threads (Cortex-A9 x2)")
    ap.add_argument("--frames", type=int, default=10, help="frames to run (camera: 0 = forever)")
    ap.add_argument("--out", default="det_out.jpg")
    ap.add_argument("--log", default="edge_detect.log")
    ap.add_argument("--fake-dets", action="store_true", help="debug: overlay fixed boxes every frame")
    args = ap.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s",
                        handlers=[logging.StreamHandler(), logging.FileHandler(args.log)])
    cv2.setNumThreads(args.threads)
    log.info("OpenCV %s, threads %d, args %s", cv2.__version__, cv2.getNumThreads(), vars(args))
    model = YoloFastest(args.model_dir, args.size)

    if args.camera:
        factory = (lambda ol: PlResize(ol, CAM_W, CAM_H, args.size)) if args.pl else (lambda ol: CpuResize())
        run_camera(args, model, factory)
    else:
        if args.pl:
            from pynq import Overlay
            ol = Overlay(args.overlay)
            h, w = cv2.imread(args.image).shape[:2]
            pre = PlResize(ol, w, h, args.size)
        else:
            pre = CpuResize()
        run_image(args, model, pre)


if __name__ == "__main__":
    main()
