# automate-youtube.py

import os
import re
import time
import datetime

import praw
from praw.models import Redditor, Comment, MoreComments

import json
import codecs

import freetype

from gtts import gTTS
from pydub import AudioSegment

import numpy as np
from PIL import Image, ImageDraw, ImageFont
import cv2
import subprocess

# Colors
RED    = (255,   0,   0, 1)
GREEN  = (  0, 255,   0, 1)
BLUE   = (  0,   0, 255, 1)
CYAN   = (  0, 255, 255, 1)
PINK   = (252,  17, 154, 1)
YELLOW = (252, 248,  22, 1)
ORANGE = (252, 127,  17, 1)
MAROON = ( 68,   2,   2, 1)


# Fonts 
comment_font = freetype.Face('./fonts/Roboto-Regular.ttf')
comment_font_sz = 32
comment_font.set_char_size(comment_font_sz * 64)
comment_font.load_char('A')
comment_font_height = comment_font.height >> 6

header_font = freetype.Face('./fonts/Roboto-Regular.ttf')
header_font_sz = 24
header_font.set_char_size(header_font_sz * 64)
header_font.load_char('A')
header_font_height = header_font.height >> 6

op_font = freetype.Face('./fonts/Roboto-Bold.ttf')
op_font_sz = 20
op_font.set_char_size(op_font_sz * 64)
op_font.load_char('A')
op_font_height = op_font.height >> 6


# Images
upvote_img = Image.open('./res/upvote.png').convert("RGBA")
upvote_dim = (int(upvote_img.width / 5), int(upvote_img.height / 5))
upvote_img = upvote_img.resize(upvote_dim)

downvote_img  = Image.open('./res/downvote.png').convert("RGBA")
downvote_dim = (int(downvote_img.width / 5), int(downvote_img.height / 5))
downvote_img  = downvote_img.resize(downvote_dim)

footer_img  = Image.open('./res/comment_footer.png').convert("RGBA")
footer_img_dim = (int(footer_img.width / 2), int(footer_img.height / 2))
footer_img = footer_img.resize(footer_img_dim)


# Video dimensions and measurements
screen_height, screen_width = 1080, 1920 
aspect = float(screen_width / screen_height)
fps = 30
background_color = (26, 26, 27, 0)

text_width_cutoff  = int(screen_width * 0.96)
text_height_cutoff = int(screen_height * 0.85)
text_start_x  = screen_width - text_width_cutoff
text_start_y  = screen_height - text_height_cutoff

magic_spacing_coefficient = 1.2
line_spacing = int((comment_font.height >> 6) * magic_spacing_coefficient)
paragraph_spacing = int(line_spacing * 1.2)

sentence_end_pad = 25

indent_off  = 50
header_off  = 50
sidebar_off = 50, 50

vote_img_pad = 100
comment_end_pad = footer_img.height + 100

pane_y = 0
total_chain_height = 0
img_height = 0


# Project Structure
working_dir = 'build-vid/'
temp_dir    = working_dir + 'tmp/'

file_names_txt_file = working_dir + 'comment_videos.txt'

na_video_name  = 'audioless_video.mp4'
audio_name  = 'audio.mp3'
static_video_name = 'static.mp4'
final_video_name = 'final.mp4'
comment_video_name_base = 'comment'
chain_video_name_base   = 'chain'

comment_n = 0

acronym_map = {
    'OP': 'oh pee',                    'op': 'oh pee',
    'LOL': 'ell oh ell',               'lol': 'ell oh ell',              'Lol': 'el oh el',
    'IIRC': 'if i recall correctly',   'iirc': 'if i recall correctly',
    'AFAIK': 'as far as i know',       'afaik': 'as far as i know',
    'DAE': 'does anyone else',         'dae': 'does anyone else',
    'ICYMI': 'in case you missed it',  'icymi': 'in case you missed it',
    'tldr': 'too long didnt read',     'TL;DR': 'too long didnt read',
    'TIL': 'today i learned',          'til': 'today i learned',
    'IDK': 'i dont know',              'idk': 'i dont know',
    'NGL': 'not gonna lie',            'ngl': 'not gonna lie',
    'LPT': 'life pro tip',             'lpt': 'life pro tip',
    'AITA': 'am i the asshole',        'aita': 'am i the asshole',
    'YTA': 'you\'re the asshole',      'yta': 'you\'re the asshole',
    'NTA': 'not the asshole',          'nta': 'not the asshole',
}

def replace_acronyms(text):
    words = re.findall(r'\b\w+\b', text)
    pattern = r'\b(' + '|'.join(acronym_map.keys()) + r')\b'
    return re.sub(pattern, lambda x: acronym_map[x.group()], text)

def flatten(lst):
    flattened_list = []
    for item in lst:
        if isinstance(item, list):
            flattened_list.extend(flatten(item))
        else:
            flattened_list.append(item)
    return flattened_list


debug = False
#debug = True

def LOG(title, message, pos=''):
    if len(title) > 32:
        title = title[:32]
    title = '[' + title + ']'
    if len(message) > 48:
        message = message[:48] + '...'
    print('{:<32}'.format(title), end='')
    print(' | {:<16}'.format(str(pos)), end='')
    if message:
        print(f' | {message}')
        return
    print(' | \n', end='')


def draw_debug_line_y(img, y, color):
    if not debug:
        return
    draw = ImageDraw.Draw(img)
    dbg_ln_start, dbg_ln_end = (0, y), (screen_width, y)
    draw.line([dbg_ln_start, dbg_ln_end], fill=color, width=2)

def draw_debug_line_x(img, x, color):
    if not debug:
        return
    draw = ImageDraw.Draw(img)
    dbg_ln_start, dbg_ln_end = (x, 0), (x, screen_height)
    draw.line([dbg_ln_start, dbg_ln_end], fill=color, width=2)


def get_paragraphs(content):
    return [s for s in content.split("\n") if s]

# TODO split on "..." as well
def get_sentences(content):
    return [s.strip() + (content[content.find(s)+len(s)]) 
            for s in re.split("[!?.]", content) if s]
    #sents = [s for s in re.split("[!?.]", content) if s]
    #print(sents)

def cleanup_text(text):
    text = text.strip()
    if text[-1] not in ['.','!','?']:
        text += '.'
    return text


def create_audio_file(text, file_name):
    path = os.path.join(temp_dir, file_name)
    text = replace_acronyms(text)
    tts = gTTS(text=text, lang='en')
    tts.save(os.path.join(temp_dir, file_name))
    audio = AudioSegment.from_file(path, format='mp3')
    duration = audio.duration_seconds
    del audio
    return duration

def create_comment_audio(comment_body):
    durations, audio_file_names, n = [], [], 1
    for paragraph in get_paragraphs(comment_body):
        for sentence in get_sentences(paragraph):
            file_name = 'audio' + str(n) + '.mp3'
            audio_file_names.append(os.path.join(temp_dir, file_name))
            durations.append(create_audio_file(sentence, file_name))
            n += 1
    audio = AudioSegment.from_file(audio_file_names[0], format='mp3')
    for file_name in audio_file_names[1:]:
        audio += AudioSegment.from_file(file_name, format='mp3')
    audio.export(os.path.join(temp_dir, audio_name))
    return durations

def points_str(npoints):
    multiplier = ''
    if npoints >= 1000000:
        npoints = npoints // 100000
        multiplier = 'm'
    elif npoints >= 1000:
        npoints = npoints // 1000
        multiplier = 'k'
    return str(npoints)[:-1] + '.' + str(npoints)[-1] + multiplier + ' points'

def time_ago_str(created_utc):
    time_ago = int(time.time()) - int(created_utc)
    if time_ago > 31536000:
        n, s = time_ago // 31536000, 'year'
    elif time_ago > 2678400:
        n, s = time_ago // 2678400,  'month'
    elif time_ago > 604800:
        n, s = time_ago // 604800,   'week'
    elif time_ago > 86400:
        n, s = time_ago // 86400,    'day'
    elif time_ago > 3600:
        n, s = time_ago // 3600,     'hour'
    elif time_ago > 60:
        n, s = time_ago // 60,       'minute'
    else:
        n, s = time,                 'second'
    if n > 1:
        s += 's'
    return str(n) + ' ' + s + ' ago'



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

def comment_body_height(comment_body, width_box):
    start_x, end_x = width_box
    x, y = start_x, 0

    last_y = y
    for paragraph in get_paragraphs(comment_body):
        for sentence in get_sentences(paragraph):
            sent_width, sent_height, _ = get_text_size_freetype(sentence, comment_font)
            if x + sent_width > int(end_x * 0.9):
                lines = wrap_text(sentence, width_box, comment_font, (x, y))
            else:
                lines = [sentence]
            first_line_width = get_text_size_freetype(lines[0], comment_font)[0]
            x += first_line_width + sentence_end_pad
            if len(lines) == 1:
                continue;
            x = start_x
            y += line_spacing
            for _ in range(len(lines[1:]) - 1):
                y += line_spacing
            x += get_text_size_freetype(lines[-1], comment_font)[0] 
        x, y = start_x, y + paragraph_spacing
    return y

def compute_comment_height(comment, width_box):
    body_h = comment_body_height(comment['body'], width_box)
    return header_off + body_h + comment_end_pad - header_off


def total_comment_height(comment, width_box):
    start_x, end_x = width_box
    h = compute_comment_height(comment, width_box)
    if comment.get('replies') is None:
        return h
    for reply in comment['replies']:
        h += total_comment_height(reply, (start_x + indent_off, end_x))
    return h

def compute_line_height(comment, width_box):
    start_x, end_x = width_box
    body_height = comment_body_height(comment['body'], width_box)
    height = body_height - downvote_img.height + comment_end_pad - header_off - 25
    if comment.get('replies') is None:
        return height
    for reply in comment['replies']:
        height += total_comment_height(reply, (start_x + indent_off, end_x))
    return height



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

def draw_header(img, pos, username, npoints, created_utc, is_submitter, medals):
    (x, y) = pos[0], pos[1] - header_off
    draw  = ImageDraw.Draw(img)
    draw_debug_line_y(img, y, PINK)

    # write the username above the image
    username_color = (22, 210, 252, 1)
    (x, y) = draw_string_to_image('/u/' + username, img, (x, y), header_font, username_color)
    x += 10

    if is_submitter:
        (x, y) = draw_string_to_image('OP', img, (x, y), op_font, RED)
        x += 10

    # write the points and time duration after the username 
    text_color = (255, 255, 255, 1)
    string = ' •   ' + points_str(npoints) + '   •   ' + time_ago_str(created_utc)
    (x, y) = draw_string_to_image(string, img, (x, y), header_font, text_color)

def draw_sidebar(img, pos, line_height):
    (x, y) = pos[0] - sidebar_off[0], pos[1] - sidebar_off[1]

    # draw upvote/downvote images
    img.paste(upvote_img, (x, y), upvote_img)
    img.paste(downvote_img, (x, y + 50), downvote_img)

    # draw the indentation line
    draw = ImageDraw.Draw(img)
    line_color = (40, 40, 40, 1)
    x_off = upvote_dim[0] / 2
    line_start = (x + x_off, y + vote_img_pad)
    line_end   = (x + x_off, y + vote_img_pad + line_height)
    draw.line([line_start, line_end], fill=line_color, width=5)

def draw_footer(img, pos):
    x, y = pos
    img.paste(footer_img, (x, y), footer_img)
    return (x, y)



def get_subimage_at_y(img, y, WIDTH, sub_height):
    image_np = np.array(image)
    np.array(image)[pane_y:pane_y + screen_height, 0:screen_width, :]
    sub_image = image_np[y:y + sub_height, 0:WIDTH, :]
    return sub_image


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
def write_sentence(text, img, pos, width_box, font, color):
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
    y += line_spacing

    last_y = y
    for n, line in enumerate(lines[1:]):
        (x, y) = draw_string_to_image(line, img, (start_x, y), font, color)
        last_y = y
        y += line_spacing

    # debug
    (x, y) = (x + sentence_end_pad, last_y)
    draw_debug_line_y(img, y, GREEN)
    return (x, y)



def write_paragraph(paragraph, img, pos, width_box, font, color):
    x, y  = pos
    start_x, end_x = width_box

    draw_debug_line_y(img, y, RED)

    global pane_y
    frames = []
    LOG('START PARAGRAPH', '', (x, y))
    for sentence in get_sentences(paragraph):
        (x, y) = write_sentence(sentence, img, (x, y), (start_x, end_x), font, color)
        frames.append(np.array(img)[pane_y:pane_y + screen_height, 0:screen_width, :])
        # scroll pane
        if y - pane_y > screen_height:
            if img_height - y < screen_height:
                pane_y = img_height - screen_height
            else:
                pane_y = y - text_start_y

    LOG('END PARAGRAPH', '')
    (x, y) = start_x, y + paragraph_spacing
    draw_debug_line_y(img, y, RED)
    return frames, (x, y)


def write_comment(comment, img, pos):
    x, y = pos
    width_box = (x, text_width_cutoff)
    color = (255, 255, 255, 1)
    frames = []

    draw_debug_line_x(img, width_box[0], BLUE)
    draw_debug_line_x(img, width_box[1], BLUE)

    draw_debug_line_y(img, y, YELLOW)
    body_height_dbg = comment_body_height(comment['body'], width_box)
    draw_debug_line_y(img, y + body_height_dbg, YELLOW)
    total_height_dbg = total_comment_height(comment, width_box)
    if comment_n == 0:
        draw_debug_line_y(img, y + total_height_dbg, CYAN)
    else:
        draw_debug_line_y(img, y + total_height_dbg, RED)


    LOG('START WRITE COMMENT', comment['body'])
    for paragraph in get_paragraphs(comment['body']):
        paragraph_frames, (x, y) = write_paragraph(paragraph, img, (x, y), width_box, comment_font, color)
        frames = frames + paragraph_frames
    LOG('END WRITE COMMENT', '', (x, y))
    return frames, (x, y)




def create_comment_frames(comment, img, start):
    x, y = start

    # draw sidebar
    line_height = compute_line_height(comment, (x, text_width_cutoff))
    draw_sidebar(img, (x, y), line_height)

    # draw header
    draw_header(img, (x, y), comment['author'], comment['score'], comment['created_utc'], comment['is_submitter'], '')

    # write comment and create new frame for each sentence
    frames, (x, y) = write_comment(comment, img, (x, y))

    # draw comment footer to last frame
    (x, y) = draw_footer(img, (x, y))
    draw_debug_line_y(img, y, MAROON)
    (x, y) = (x, y + comment_end_pad)
    draw_debug_line_y(img, y, MAROON)
    draw_debug_line_y(img, y, ORANGE)

    #frames[-1] = np.array(img)
    frames[-1] = np.array(img)[pane_y:pane_y + screen_height, 0:screen_width, :]
    return frames, (x, y)


# creates audio for each sentence of the comment body with gTTs and combines
# them into one long mp3 file 
#
# creates a video that displays each sentence as it is spoken and holds it 
# for the duration of its respective spoken duration from gTTS, with no audio
# 
# combines the audioless video and the audio with ffmpeg for a video of just this comment
# 
# returns the img given, in case this comment is part of a tree
def create_comment_video(comment, img, start):
    x, y = start

    # scroll pane
    global pane_y
    comment_height = compute_comment_height(comment, (x, text_width_cutoff))
    if y + comment_height > pane_y + screen_height:
        old_pane_y = pane_y
        if img_height - y < screen_height:
            pane_y = img_height - screen_height
        else:
            pane_y = y - text_start_y
        LOG('PANE SHIFT', '', (old_pane_y, pane_y))

    durations      = create_comment_audio(comment['body'])
    frames, (x, y) = create_comment_frames(comment, img, (x, y))

    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    out    = cv2.VideoWriter(os.path.join(temp_dir, na_video_name), fourcc, fps, (screen_width, screen_height))
    for frame, duration in list(zip(frames, durations)):
        cv2_frame = cv2.cvtColor(frame, cv2.COLOR_RGBA2BGR)
        for _ in range(int(fps * duration)):
            out.write(cv2_frame)
    out.release()
    cv2.destroyAllWindows()

    global comment_n
    out_file_name = comment_video_name_base + str(comment_n) + '.mp4'
    #subprocess.run(f"ffmpeg -i {temp_dir}{na_video_name} -i {temp_dir}{audio_name} -c copy -map 0:v:0 -map 1:a:0 ./{working_dir}{out_file_name}", shell=True, timeout=120)
    subprocess.run(f"ffmpeg -i {temp_dir}{na_video_name} -i {temp_dir}{audio_name} -c copy -map 0:v:0 -map 1:a:0 ./{working_dir}{out_file_name} > /dev/null 2>&1", shell=True, timeout=120)
    LOG('VIDEO CREATED', out_file_name)
    comment_n += 1

    out_file_names = [out_file_name]
    if 'replies' in comment:
        for reply in comment['replies']:
            (_, y), reply_out_file_names = create_comment_video(reply, img, (x + indent_off, y))
            out_file_names.append(flatten(reply_out_file_names))
    return (x, y), flatten(out_file_names)


class MoreRepliesThanDesiredError(Exception):
    pass

# Intended for use on top level comment of each comment chain
# before chain_video generation
def more_replies_than_desired(comment):
    if len(comment['replies']) > 3:
        return True
    # TODO import more comments with praw
    #for reply0 in comment['replies']:
    #    for key in reply0.keys():
    #        print(key)
    #    if len(reply0['replies']) > 3:
    #        return True
    #    for reply1 in reply0['replies']:
    #        if len(reply1['replies']) > 0:
    #            return True
    return False

# creates several subvideos and makes a call to ffmpeg to concatenate them
def create_comment_chain_video(comment, chain_n):
    #if (more_replies_than_desired(comment)):
    #    raise MoreRepliesThanDesiredError("too many replies doofus.")

    # scroll pane
    global pane_y, total_chain_height, img_height
    img_height = screen_height
    total_chain_height = total_comment_height(comment, (text_start_x, text_width_cutoff))
    start_y = int((screen_height / 2) - (total_chain_height / 2))

    if total_chain_height > text_height_cutoff:
        start_y = text_start_y
        img_height = total_chain_height + (2 * text_start_y)

    LOG('START Y', str(start_y))
    LOG('TOTAL CHAIN HEIGHT', str(total_chain_height))
    LOG('IMAGE HEIGHT', str(img_height))

    global comment_n
    comment_n = 0
    (x, y) = (text_start_x, start_y)
    img = Image.new("RGBA", (screen_width, img_height), background_color)

    end, file_names = create_comment_video(comment, img, (x, y))

    with open(file_names_txt_file, 'w') as f:
        for file_name in file_names:
            f.write('file \'' + file_name + '\'\n')

    out_file_name = chain_video_name_base + str(chain_n) + '.mp4'
    #subprocess.run(f"ffmpeg -f concat -safe 0 -i {file_names_txt_file} -c copy ./{working_dir}{out_file_name}", shell=True, timeout=120)
    subprocess.run(f"ffmpeg -f concat -safe 0 -i {file_names_txt_file} -c copy ./{working_dir}{out_file_name} > /dev/null 2>&1", shell=True, timeout=120)
    LOG('VIDEO CREATED', out_file_name)

    return out_file_name



# TODO partially implemented not working
def create_final_video(post):
    chain_n = 0
    file_names = []

    for comment in post['comments']:
        chain_file_name = create_comment_chain_video(comment, chain_n)
        file_names.append(chain_file_name)
        chain_n += 1

    with open(file_names_txt_file, 'w') as f:
        for file_name in file_names:
            f.write('file \'' + file_name + '\'\n')
            f.write('file \'' + static_video_name + '\'\n')

    LOG('CREATING FINAL VIDEO...', '')
    subprocess.run(f"ffmpeg -f concat -safe 0 -i {file_names_txt_file} -c copy {final_video_name}", shell=True, timeout=120)
    LOG('FINAL VIDEO CREATED', '')


if __name__ == '__main__':

    score_limit = 1000
    max_n_replies = 4
    with codecs.open('posts.json', 'r', 'utf-8') as posts_file:
        posts = prune_posts(json.load(posts_file), score_limit, max_n_replies)

    comment = posts[0]['comments'][0]
    #for i in range(1, 2):
    #    comment['replies'] += posts[i]['comments'][0]['replies']
    #comment['body'] = cleanup_text(comment['body'])
    #for reply in comment['replies']:
    #    reply['body'] = cleanup_text(reply['body'])

    #for i in range(1, 2):
    #    for reply in posts[i]['comments'][0]['replies']:
    #        comment['body'] += cleanup_text(reply['body']) + '\n'
    #comment['body'] = cleanup_text(comment['body'])
    #print(comment['body'])


    create_comment_chain_video(comment, 1)
    #create_final_video(posts[0]["comments"][:2])


