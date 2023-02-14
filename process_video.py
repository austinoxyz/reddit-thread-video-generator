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

#for frame in frames:
#    plt.imshow(frame)
#    plt.show()

fps = 30
fourcc = cv2.VideoWriter_fourcc(*"mp4v")
out    = cv2.VideoWriter('res/new_static_vid.mp4', fourcc, fps, (1080, 1920))
video_len = 1.5 # seconds
nframes = int(fps * video_len)
for i in range(nframes):
    out.write(frames[i % len(frames)])
out.release()
cv2.destroyAllWindows()
