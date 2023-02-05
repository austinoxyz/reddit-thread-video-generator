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

screen_height, screen_width = 1080, 1920 

aspect = float(screen_width / screen_height)
fps = 30
background_color = (26, 26, 27, 0)


text_width_cutoff = int(screen_width * 0.96)
text_start_x  = screen_width - text_width_cutoff

text_height_cutoff = int(screen_height * 0.90)
text_start_y  = screen_height - text_height_cutoff

comment_font = freetype.Face('./Roboto-Regular.ttf')
comment_font_sz = 32
comment_font.set_char_size(comment_font_sz * 64)
comment_font.load_char('A')
comment_font_height = comment_font.height >> 6

header_font = freetype.Face('./Roboto-Regular.ttf')
header_font_sz = 24
header_font.set_char_size(header_font_sz * 64)
header_font.load_char('A')
header_font_height = header_font.height >> 6

magic_spacing_coefficient = 1.2
line_spacing = int((comment_font.height >> 6) * magic_spacing_coefficient)


indentation_offset = 50
comment_end_padding = 80

sidebar_offset = -50, -30
header_offset  =   0, -50
footer_offset  =   0, -10


upvote_img  = Image.open('./res/upvote.png').convert("RGBA")
upvote_size = (int(upvote_img.width / 5), int(upvote_img.height / 5))
upvote_img  = upvote_img.resize(upvote_size)

downvote_img  = Image.open('./res/downvote.png').convert("RGBA")
downvote_size = (int(downvote_img.width / 5), int(downvote_img.height / 5))
downvote_img  = downvote_img.resize(downvote_size)

footer_img  = Image.open('./res/comment_footer.png').convert("RGBA")
size = (int(footer_img.width / 2), int(footer_img.height / 2))
footer_img  = footer_img.resize(size)

footer_padding = footer_img.height + 10

temp_dir    = 'tmp/'
working_dir = 'build-vid/'

comment_video_name_base = 'comment'
chain_video_name_base = 'chain'

file_names_txt_file = working_dir + 'comment_videos.txt'

na_video_name  = 'audioless_video.mp4'
audio_name  = 'audio.mp3'
static_video_name = 'static.mp4'
final_video_name = 'final.mp4'

comment_n = 0

#  DEBUG DEBUG DEBUG DEBUG DEBUG DEBUG DEBUG DEBUG DEBUG DEBUG DEBUG DEBUG DEBUG DEBUG
start_comment_color = (0, 255, 0, 1)
header_offset_color = (255, 0, 0, 1)
commend_end_color   = (0, 0, 255, 1)


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
    print('\n', end='')

def load_top_posts_and_best_comments(subreddit_name):
    reddit = praw.Reddit(client_id=    'Sx5GE4fYzUuNLwEg_h8k4w',
                         client_secret='0n4qkZVolBDeR2v5qq6-BnSuJyhQ7w',
                         user_agent=   'python-script')
    subreddit = reddit.subreddit(subreddit_name)
    posts = subreddit.top(limit=10, time_filter='all')
    post_data = []
    for post in posts:
        print(f"Saving top ten comments from post titled: {post.title}")
        comments = [comment for comment in post.comments.list() 
                    if not isinstance(comment, MoreComments)]
        comments.sort(key=lambda x: x.score, reverse=True)
        top_comments = comments[:10]
        comments_data = []
        for comment in top_comments:
            # not sure why this is happening to the last comment in the list
            if comment.author is None:
                continue
            subcomments = [subcomment for subcomment in comment.replies.list() 
                        if not isinstance(subcomment, MoreComments)]
            subcomments.sort(key=lambda x: x.score, reverse=True)
            top_subcomments = subcomments[:3]
            subcomments_data = []
            for subcomment in top_subcomments:
                # not sure why this is happening to the last comment in the list
                if subcomment.author is None:
                    continue
                subcomments_data.append({
                    'author': subcomment.author.name,
                    'score':  subcomment.score,
                    'permalink': subcomment.permalink,
                    'body':   subcomment.body,
                    'created_utc': subcomment.created_utc,
                    'id': subcomment.id
                })

            comments_data.append({
                'author': comment.author.name,
                'score':  comment.score,
                'permalink': comment.permalink,
                'body':   comment.body,
                'created_utc': comment.created_utc,
                'id': comment.id,
                'replies': subcomments_data
            })
        post_data.append({
            'title': post.title,
            'score': post.score,
            'url': post.url,
            'permalink': post.permalink,
            'author': post.author.name,
            'content': post.selftext,
            'comments': comments_data
        })


    with codecs.open('posts.json', 'w', 'utf-8') as json_file:
        json.dump(post_data, json_file)



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


def flatten(lst):
    flattened_list = []
    for item in lst:
        if isinstance(item, list):
            flattened_list.extend(flatten(item))
        else:
            flattened_list.append(item)
    return flattened_list

def get_paragraphs(content):
    return [s for s in content.split("\n") if s]

# TODO split on "..." as well
def get_sentences(content):
    return [s.strip() + (content[content.find(s)+len(s)]) 
            for s in re.split("[!?.]", content) if s]


def get_text_size_freetype(text, face):
    slot = face.glyph
    width, height, baseline = 0, 0, 0
    previous = 'a'
    for i, c in enumerate(text):
        face.load_char(c)
        bitmap = slot.bitmap
        height = max(height,
                     bitmap.rows + max(0,-(slot.bitmap_top-bitmap.rows)))
        baseline = max(baseline, max(0,-(slot.bitmap_top-bitmap.rows)))
        kerning = face.get_kerning(previous, c)
        width += (slot.advance.x >> 6) + (kerning.x >> 6)
        previous = c
    return width, height, baseline


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


def get_subimage_at_y(img, y, WIDTH, sub_height):
    image_np = np.array(image)
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
    slot = font.glyph
    previous = 0
    width, height, baseline = get_text_size_freetype(string, font)

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

    return img, (x, y)

    

# only contains the text within a specified width - 
# text will continue to grow downward in write_paragraph_to_image()
# so long as there are still sentences to write in the paragraph
def write_sentence_to_image(text, img, 
                            pos, width_box,
                            font, color):
    LOG('DRAW SENTENCE', text, pos)

    x, y = pos
    start_x, end_x = width_box

    text_width, text_height, _ = get_text_size_freetype(text, font)
    end_padding = 25

    if pos[0] + text_width > int(end_x * 0.9):
        lines = wrap_text(text, width_box, font, pos)
    else:
        lines = [text]

    img, (x, y) = draw_string_to_image(lines[0], img, (x, y), font, color)

    if len(lines) == 1:
        return img, (x + end_padding, y)

    y += line_spacing

    last_y = y
    for n, line in enumerate(lines[1:]):
        img, (x, y) = draw_string_to_image(line, img, (start_x, y), font, color)
        last_y = y
        y += line_spacing

    return img, (x + end_padding, last_y)


def draw_debug_line(img, y, color):
    draw = ImageDraw.Draw(img)
    dbg_ln_start, dbg_ln_end = (0, y), (screen_width, y)
    draw.line([dbg_ln_start, dbg_ln_end], fill=color, width=2)


def write_paragraph_to_image(paragraph, img, 
                             pos, width_box,
                             font, color):
    x, y  = pos
    start_x, end_x = width_box
    frames = []
    sentences = get_sentences(paragraph)
    for sentence in sentences:
        img, (x, y) = write_sentence_to_image(sentence, img, 
                                              (x, y), (start_x, end_x),
                                              font, color)
        frames.append(np.array(img))
    return frames, (x, y)


def write_comment_to_image(comment_body, img, pos):
    # debug 
    draw_debug_line(img, pos[1], (0, 255, 0, 1))
    body_height_dbg = compute_comment_body_height(comment_body, (text_start_x, text_width_cutoff))
    draw_debug_line(img, pos[1] + body_height_dbg, (255, 255, 0, 1))

    x, y = pos
    width_box = (x, text_width_cutoff)
    color = (255, 255, 255, 1)
    LOG('START WRITE COMMENT', '')
    LOG(f'BODY', comment_body)
    paragraphs = get_paragraphs(comment_body)
    frames = []
    for paragraph in paragraphs:
        LOG('START PARAGRAPH', '', (x, y))
        LOG('BODY', paragraph)
        paragraph_frames, end = write_paragraph_to_image(paragraph, img, 
                                                             (x, y), width_box, 
                                                             comment_font, color)
        LOG('END PARAGRAPH', '')
        frames = frames + paragraph_frames
        x, y = pos[0], end[1] + int(line_spacing * 1.2)
    LOG('END WRITE COMMENT', '', (x, y))
    return frames, (x, y)


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



def draw_comment_header_to_image(img, pos, 
                                 username, npoints, created_utc, medals):
    draw  = ImageDraw.Draw(img)
    text_color = (255, 255, 255, 1)
    username_color = (22, 210, 252, 1)

    draw_debug_line(img, pos[1], (255, 0, 0, 1))

    x_padding = 10
    x, y = pos

    # write the username above the image
    (x, y) = draw_string_to_image('/u/' + username, img, (x, y), header_font, username_color)[1]
    x += x_padding

    # write the points and time duration after the username 
    string = ' • ' + points_str(npoints) + ' • ' + time_ago_str(created_utc)
    (x, y) = draw_string_to_image(string, img, (x, y), header_font, text_color)[1]



def draw_comment_sidebar_to_image(img, pos, line_height):
    x, y = pos

    # load the upvote image, resize, and draw
    upvote_pos  = (x, y - 20)
    img.paste(upvote_img, upvote_pos, upvote_img)

    # load the downvote image, resize, and draw
    downvote_pos  = (x, y + 40)
    img.paste(downvote_img, downvote_pos, downvote_img)

    # draw the indentation line
    draw = ImageDraw.Draw(img)
    line_color = (40, 40, 40, 1)
    x_offset = upvote_size[0] / 2
    line_start, line_end = (x + x_offset, y + 100), (x + x_offset, y + 100 + line_height)
    draw.line([line_start, line_end], fill=line_color, width=5)




def draw_comment_footer_to_image(img, pos):

    # debug
    draw = ImageDraw.Draw(img)
    draw_debug_line(img, pos[1], (0, 255, 0, 1))
    draw_debug_line(img, pos[1] + footer_img.height, (0, 0, 255, 1))

    x, y = pos
    img.paste(footer_img, (x, y), footer_img)
    return (x, y + footer_padding)




def create_comment_frames(comment, img, start):

    x, y = start

    # draw sidebar
    sidebar_pos = x + sidebar_offset[0], y + sidebar_offset[1]
    line_height = compute_line_height(comment, (x, text_width_cutoff))
    draw_comment_sidebar_to_image(img, sidebar_pos, line_height)

    # draw header
    header_pos = x + header_offset[0], y + header_offset[1]
    draw_comment_header_to_image(img, header_pos, comment['author'], comment['score'], 
                                 comment['created_utc'], '')

    # write comment and create new frame for each sentence
    frames, (x, y) = write_comment_to_image(comment['body'], img, (x, y))

    comment_end_padding = 0
    y += comment_end_padding

    # draw comment footer to last frame
    footer_pos  = x + footer_offset[0], y + footer_offset[1]
    (x, y) = draw_comment_footer_to_image(img, (x, y))
    frames[-1] = np.array(img)
    return frames, img, (x, y + comment_end_padding + footer_padding)






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
    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    out    = cv2.VideoWriter(os.path.join(temp_dir, na_video_name), fourcc, fps, (screen_width, screen_height))
    x, y = start

    durations           = create_comment_audio(comment['body'])
    frames, img, (x, y) = create_comment_frames(comment, img, (x, y))

    for frame, duration in list(zip(frames, durations)):
        cv2_frame = cv2.cvtColor(frame, cv2.COLOR_RGBA2BGR)
        for _ in range(int(fps * duration)):
            out.write(cv2_frame)

    out.release()
    cv2.destroyAllWindows()

    global comment_n
    out_file_name = comment_video_name_base + str(comment_n) + '.mp4'
    subprocess.run(f"ffmpeg -i {temp_dir}{na_video_name} -i {temp_dir}{audio_name} -c copy -map 0:v:0 -map 1:a:0 ./{working_dir}{out_file_name} > /dev/null 2>&1", shell=True, timeout=120)
#    subprocess.run(f"ffmpeg -i {temp_dir}{na_video_name} -i {temp_dir}{audio_name} -c copy -map 0:v:0 -map 1:a:0 ./{working_dir}{out_file_name}", shell=True, timeout=120)

    LOG('VIDEO CREATED', out_file_name)
    comment_n += 1

    out_file_names = [out_file_name]

    if 'replies' in comment:
        for reply in comment['replies']:
            img, (_, y), reply_out_file_names = create_comment_video(reply, img, (x + indentation_offset, y))
            out_file_names.append(flatten(reply_out_file_names))

    return img, (x, y), flatten(out_file_names)




def compute_comment_body_height(comment_body, width_box):
    start_x, end_x = width_box
    x, y = start_x, 0
    end_padding = 25

    for paragraph in get_paragraphs(comment_body):
        for sentence in get_sentences(paragraph):
            sent_width, sent_height, _ = get_text_size_freetype(sentence, comment_font)
            if x + sent_width > int(end_x * 0.9):
                lines = wrap_text(sentence, width_box, comment_font, (x, y))
            else:
                lines = [sentence]

            first_line_width = get_text_size_freetype(lines[0], comment_font)[0]
            x += first_line_width + end_padding
            if len(lines) == 1:
                continue;
            y += line_spacing

            for line in lines[1:-1]:
                y += line_spacing
            last_line_width = get_text_size_freetype(lines[-1], comment_font)[0]
            x = start_x + last_line_width + end_padding
        x, y = start_x, y + int(line_spacing * 1.2)
    return y + line_spacing

def compute_line_height(comment, width_box):
    start_x, end_x = width_box
    #total_height = compute_total_comment_height(comment, width_box)
    body_height = compute_comment_body_height(comment['body'], width_box)
    height = body_height - downvote_img.height + footer_offset[1] + footer_img.height
    if comment.get('replies') is None:
        return height
    for reply in comment['replies']:
        height += -header_offset[1] + downvote_img.height
        height += compute_line_height(reply, (start_x + indentation_offset, end_x))
    return height

def compute_start_y(comment):
    height = compute_total_comment_height(comment, (text_start_x, text_width_cutoff))
    if height > screen_height:
        return text_start_y
    else:
        return int((screen_height / 2)  - (height / 2))

def compute_total_comment_height(comment, width_box):
    body_height = compute_comment_body_height(comment['body'], width_box)
    return -header_offset[1] + body_height + footer_offset[1] + footer_img.height



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

def prune_comment_replies(comment):
    return False

# creates several subvideos and makes a call to ffmpeg to concatenate them
def create_comment_chain_video(comment, chain_n):
    if (more_replies_than_desired(comment)):
        raise MoreRepliesThanDesiredError("too many replies doofus.")

    img = Image.new("RGBA", (screen_width, screen_height), background_color)

    global comment_n
    comment_n = 0

    #file_names = []

    #(x, y) = (text_start_x, compute_start_y(comment))
    (x, y) = (text_start_x, text_start_y)
    img, end, file_names = create_comment_video(comment, img, (x, y))

#    # TODO this is temporary. Must preprocess comment chain and compute total comment height
#    # for each comment beforehand, and loop through the "comment structure" 
#    # given by `comment` argument to the function, keeping track of 
#    (x, y) = (text_start_x, compute_start_y(comment))
#    img, end, file_name = create_comment_video(comment, img, (x, y), comment_n)
#    comment_n += 1
#    file_names.append(file_name)
#
#    # TODO temporary read above
#    (x, y) = end[0] + indentation_offset, end[1] + comment_end_padding
#    img, end, file_name = create_comment_video(comment['replies'][0], img, (x, y), comment_n)
#    comment_n += 1
#    file_names.append(file_name)
    
    out_file_name = chain_video_name_base + str(chain_n) + '.mp4'

    with open(file_names_txt_file, 'w') as f:
        for file_name in file_names:
            f.write('file \'' + file_name + '\'\n')

    subprocess.run(f"ffmpeg -f concat -safe 0 -i {file_names_txt_file} -c copy ./{working_dir}{out_file_name} > /dev/null 2>&1", shell=True, timeout=120)
    #subprocess.run(f"ffmpeg -f concat -safe 0 -i {file_names_txt_file} -c copy ./{working_dir}{out_file_name}", shell=True, timeout=120)
    LOG('VIDEO CREATED', out_file_name)

    return out_file_name



# TODO partially implemented not working
def create_final_video(comments):
    chain_n = 0
    file_names = []

    for comment in comments:
        chain_file_name = create_comment_chain_video(comment, chain_n)
        file_names.append(chain_file_name)
        chain_n += 1

    with open(file_names_txt_file, 'w') as f:
        for file_name in file_names:
            f.write('file \'' + file_name + '\'\n')
            f.write('file \'' + static_video_name + '\'\n')

    subprocess.run(f"ffmpeg -f concat -safe 0 -i {file_names_txt_file} -c copy {working_dir}{out_file_name}", shell=True, timeout=120)


if __name__ == '__main__':
    with codecs.open('posts.json', 'r', 'utf-8') as posts_file:
        posts = json.load(posts_file)

    comment = posts[0]["comments"][0]
    #comment['replies'] = [comment['replies'][0]]
    #comment['replies'] = comment['replies'][:3]
    #comment['replies'][0]['replies'] = []

    #width_box = (text_start_x, text_width_cutoff)
    #comment_body = comment['body']
    #body_height  = compute_comment_body_height(comment_body, width_box)
    #total_height = compute_total_comment_height(comment, width_box)
    #line_height  = compute_line_height(comment, width_box)
    #print(body_height)
    #print(total_height)
    #print(line_height)

    #print(compute_comment_body_height(comment['replies'][0]['body'], width_box))

    create_comment_chain_video(comment, 1)
    #create_final_video(posts[0]["comments"][:2])



