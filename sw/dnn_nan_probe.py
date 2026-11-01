# Find the first layer producing NaN/Inf in OpenCV DNN for the YOLO-Fastest cfg (board-side debug)
import sys
import cv2
import numpy as np

cfg, weights, img = sys.argv[1:4]
net = cv2.dnn.readNetFromDarknet(cfg, weights)
blob = cv2.dnn.blobFromImage(cv2.resize(cv2.imread(img), (320, 320)), 1 / 255.0, swapRB=True)
net.setInput(blob)
names = net.getLayerNames()
outs = net.forward(list(names[1:]))
for name, o in zip(names[1:], outs):
    if not np.isfinite(o).all():
        lid = net.getLayerId(name)
        print("first non-finite layer:", name, net.getLayer(lid).type, o.shape)
        break
else:
    print("all finite")
