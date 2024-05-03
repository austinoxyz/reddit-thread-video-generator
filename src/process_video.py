import cv2
import numpy as np

import matplotlib
import matplotlib.pyplot as plt

matplotlib.use('TKAgg', force=True)

cap = cv2.VideoCapture('res/static.mp4')
frames = []
while cap.isOpened():
    ret, frame = cap.read()
    if ret:
        frames.append(frame)
    else:
        break;
cap.release()

print(f"type: {str(type(frames[0]))}")
print(f"(width, height) = {str(frames[0].shape)}")
print(f"dtype = {str(frames[0].dtype)}")
print(f"# frames = {len(frames)}")

fps = 30
fourcc = cv2.VideoWriter_fourcc(*"mp4v")
out    = cv2.VideoWriter('res/new_static_vid.mp4', fourcc, fps, (1080, 1920))
video_len = 1.5 # seconds
nframes = int(fps * video_len)

framen, i = 0, 0
while True:
    out.write(frames[i % len(frames)])
    framen += 1
    if framen % 7 == 0:
        i += 1
    if framen > nframes:
        break;



for i in range(nframes):
    out.write(frames[i % len(frames)])
out.release()
cv2.destroyAllWindows()
