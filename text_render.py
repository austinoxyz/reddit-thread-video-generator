# textrender.py

import freetype
from PIL import Image, ImageDraw
import numpy as np

from text_clean import clean_comment_bodies, get_paragraphs, get_sentences
from util import *

# TODO find a better place for this or 
# refactor it out of global scope
pane_y = 0

screen_height, screen_width = 1080, 1920 
aspect = float(screen_width / screen_height)

sentence_end_pad = 25
text_width_cutoff  = int(screen_width * 0.96)
text_height_cutoff = int(screen_height * 0.85)
text_start_x  = screen_width - text_width_cutoff
text_start_y  = screen_height - text_height_cutoff

def get_text_size_freetype(text, face):
    slot = face.glyph
    width, height, baseline = 0, 0, 0
    previous = 'a'
    for i, c in enumerate(text):
        face.load_char(c)
        bitmap = slot.bitmap
        height = max(height, bitmap.rows + max(0, -(slot.bitmap_top - bitmap.rows)))
        baseline = max(baseline, max(0, -(slot.bitmap_top - bitmap.rows)))
        kerning = face.get_kerning(previous, c)
        width += (slot.advance.x >> 6) + (kerning.x >> 6)
        previous = c
    return width, height, baseline

def get_bounded_text_height(text, font, width_box):
    start_x, end_x = width_box
    x, y = start_x, 0
    spacing = int((font.height >> 6) * 1.2)

    last_y = y
    for paragraph in get_paragraphs(text):
        for sentence in get_sentences(paragraph):
            sent_width, sent_height, _ = get_text_size_freetype(sentence, font)
            if x + sent_width > int(end_x * 0.9):
                lines = wrap_text(sentence, width_box, font, (x, y))
            else:
                lines = [sentence]
            first_line_width = get_text_size_freetype(lines[0], font)[0]
            x += first_line_width + sentence_end_pad
            if len(lines) == 1:
                continue;
            x = start_x
            y += spacing
            for _ in range(len(lines[1:]) - 1):
                y += spacing
            x += get_text_size_freetype(lines[-1], font)[0]
        x, y = start_x, y + int(spacing * 1.2)
    return y


def wrap_text(text, width_box, font, pos):
    wrapped_text = []
    line = ''
    words = text.split(' ')

    begin = pos[0]
    start_x, end_x = width_box
    max_width = end_x - start_x

    for word in words:
        text_width = get_text_size_freetype(line + ' ' + word, font)[0]
        if begin + text_width < max_width:
            line += ' ' + word
        else:
            if len(wrapped_text) == 0:
                begin = start_x
            wrapped_text.append(line)
            line = word

    wrapped_text.append(line)
    return [line for line in wrapped_text if line != '']


def draw_bitmap_to_image(bitmap, img, pos, color):
    x, y = pos
    x_max = x + bitmap.width
    y_max = y + bitmap.rows

    for p, i in enumerate(range(x, x_max)):
        for q, j in enumerate(range(y, y_max)):
            if i < 0 or j < 0 or i >= img.width or j >= img.height:
                continue;

            f = int(bitmap.buffer[q * bitmap.width + p]) # intensity
            a = int(color[3] * 255)
            r = int(f * color[0] * a / (255 * 255))
            g = int(f * color[1] * a / (255 * 255))
            b = int(f * color[2] * a / (255 * 255))

            if f > 32:
                pixel = img.getpixel((i, j))
                new_pixel = pixel[0] | r, pixel[1] | g, pixel[2] | b, a
                img.putpixel((i, j), new_pixel)



# draws endlessly to the right with no logic otherwise
def draw_string_to_image(string, img, pos, font, color):
    x, y = pos
    width, height, baseline = get_text_size_freetype(string, font)

    slot = font.glyph
    previous = 0
    for c in string:
        font.load_char(c)
        bitmap = font.glyph.bitmap

        c_img = Image.new("RGBA", (bitmap.width, bitmap.rows), 0)
        draw_bitmap_to_image(bitmap, c_img, (0, 0), color)

        draw_x = x + font.glyph.bitmap_left
        draw_y = y + height - baseline - font.glyph.bitmap_top 
        img.paste(c_img, (draw_x, draw_y), c_img)

        advance = font.glyph.advance.x >> 6
        kerning = font.get_kerning(previous, c).x >> 6
        x += advance + kerning
        previous = c
    return (x, y)

    

# only contains the text within a specified width -
# text will continue to grow downward
# so long as there are still sentences to write in the paragraph
def write_sentence(text, img, pos, width_box, font, spacing, color):
    x, y = pos
    draw_debug_line_y(img, y, GREEN)
    start_x, end_x = width_box

    text_width, text_height, _ = get_text_size_freetype(text, font)
    if pos[0] + text_width > int(end_x * 0.9):
        lines = wrap_text(text, width_box, font, pos)
    else:
        lines = [text]

    LOG('DRAWING SENTENCE', text, pos)
    (x, y) = draw_string_to_image(lines[0], img, (x, y), font, color)
    if len(lines) == 1:
        return (x + sentence_end_pad, y)
    y += spacing

    last_y = y
    for n, line in enumerate(lines[1:]):
        (x, y) = draw_string_to_image(line, img, (start_x, y), font, color)
        last_y = y
        y += spacing

    # debug
    (x, y) = (x + sentence_end_pad, last_y)
    draw_debug_line_y(img, y, GREEN)
    return (x, y)



def write_paragraph(paragraph, img, pos, width_box, font, spacing, color):
    x, y  = pos
    start_x, end_x = width_box

    draw_debug_line_y(img, y, RED)

    global pane_y
    frames = []
    LOG('START PARAGRAPH', '', (x, y))
    for sentence in get_sentences(paragraph):
        (x, y) = write_sentence(sentence, img, (x, y), (start_x, end_x), font, spacing, color)
        frames.append(np.array(img)[pane_y:pane_y + screen_height, 0:screen_width, :])
        # scroll pane
        if y - pane_y > screen_height:
            if img_height - y < screen_height:
                pane_y = img_height - screen_height
            else:
                pane_y = y - text_start_y

    LOG('END PARAGRAPH', '')
    (x, y) = start_x, y + int(spacing * 1.2)
    draw_debug_line_y(img, y, RED)
    return frames, (x, y)


font_metric_string = ''.join([chr(c) for c in range(32, 256)])

font_registry = {}

def add_font_to_registry(fpath, fontsize, name):
    font = freetype.Face(fpath)
    font.set_char_size(fontsize * 64)
    height, baseline = get_text_size_freetype(font_metric_string, font)[1:]
    font_registry[name] = {'height':height, 'baseline':baseline}

def new_font(fpath, fontsize):
    font = freetype.Face(fpath)
    font.set_char_size(fontsize * 64)
    return font


