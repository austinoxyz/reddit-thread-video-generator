from freetype import *
import matplotlib
import numpy
from PIL import Image, ImageDraw, ImageFont

if __name__ == '__main__':
    import numpy
    import matplotlib.pyplot as plt

    face = Face('./NotoSansMono-Regular.ttf')
    text = 'Hello World !'
    face.set_char_size(int(24 * 64 * 4))
    slot = face.glyph

    # First pass to compute bbox
    width, height, baseline = 0, 0, 0
    previous = 0
    for i,c in enumerate(text):
        face.load_char(c)
        bitmap = slot.bitmap
        height = max(height,
                     bitmap.rows + max(0,-(slot.bitmap_top-bitmap.rows)))
        baseline = max(baseline, max(0,-(slot.bitmap_top-bitmap.rows)))
        kerning = face.get_kerning(previous, c)
        width += (slot.advance.x >> 6) + (kerning.x >> 6)
        previous = c

    Z = numpy.zeros((height,width), dtype=numpy.ubyte)

    # Second pass for actual rendering
    x, y = 0, 0
    previous = 0
    for c in text:
        face.load_char(c)
        bitmap = slot.bitmap
        top = slot.bitmap_top
        left = slot.bitmap_left
        w,h = bitmap.width, bitmap.rows
        y = height-baseline-top
        kerning = face.get_kerning(previous, c)
        x += (kerning.x >> 6)
        Z[y:y+h,x:x+w] += numpy.array(bitmap.buffer, dtype='ubyte').reshape(h,w)
        x += (slot.advance.x >> 6)
        previous = c

    img = Image.new("L")

    scale = 1
    plt.figure(figsize=(scale, scale*Z.shape[0]/float(Z.shape[1])))
    plt.imshow(Z, interpolation='nearest', origin='upper', cmap=plt.cm.gray)
    plt.xticks([]), plt.yticks([])
    plt.show()
