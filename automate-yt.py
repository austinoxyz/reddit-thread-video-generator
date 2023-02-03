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



#base_dir    = '/home/anon/Videos/automate-yt/'
#temp_dir    = base_dir + 'tmp/'
#working_dir = base_dir + 'working/'

temp_dir    = 'tmp/'
working_dir = 'build-vid/'

na_video_name  = 'audioless_video.mp4'
audio_name  = 'audio.mp3'

file_names_txt_file = working_dir + 'comment_videos.txt'

comment_video_name_base = 'comment'
chain_video_name_base = 'chain'

static_video_name = 'static.mp4'

final_video_name = 'final.mp4'

acronym_map = {
    'OP': 'oh pee',                    'op': 'oh pee',
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


def get_paragraphs(content):
    return [s for s in content.split("\n") if s]

# TODO split on "..." as well
def get_sentences(content):
    return [s.strip() + (content[content.find(s)+len(s)]) 
            for s in re.split("[!?.]", content) if s]



def get_text_size(font, text):
    bbox = font.getbbox(text)
    return (bbox[2] - bbox[0], bbox[3] - bbox[1])

def get_text_size_freetype(text, face):
    slot = face.glyph
    # First pass to compute bbox
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


    x, y = pos
    print(f"[DRAW   SENTENCE] ({(x,y)}): {text}")
    start_x, end_x = width_box
    last_y = y

    text_width, text_height, _ = get_text_size_freetype(text, font)
    end_padding = 25

    if pos[0] + text_width > int(end_x * 0.9):
        lines = wrap_text(text, width_box, font, pos)
    else:
        lines = [text]

    img, (x, y) = draw_string_to_image(lines[0], img, (x, y), font, color)
    line_width = get_text_size_freetype(lines[0], font)[0]

    if len(lines) == 1:
        return img, (x + end_padding, y)

    y += line_spacing

    for n, line in enumerate(lines[1:]):
        img, (x, y) = draw_string_to_image(line, img, (start_x, y), font, color)
        last_y = y
        y += line_spacing

    return img, (x + end_padding, last_y)




def write_paragraph_to_image(paragraph, img, 
                             pos, width_box,
                             font, color):

    x, y  = pos
    max_x, max_y = width_box
    frames = []
    sentences = get_sentences(paragraph)
    for sentence in sentences:
        img, (x, y) = write_sentence_to_image(sentence, img, 
                                              (x, y), (pos[0], max_x),
                                              font, color)
        frames.append(np.array(img))
    return frames, (x, y)




def write_comment_to_image(comment_body, img, 
                           pos, width_box):
    x, y = pos
    max_x, max_y = width_box
    color = (255, 255, 255, 1)
    print("[START WRITE COMMENT]")
    print(f"Body: {comment_body}", end='\n\n')
    paragraphs = get_paragraphs(comment_body)
    print(f"Paragraphs({len(paragraphs)}): {paragraphs}", end='\n\n')
    frames = []
    for paragraph in paragraphs:
        print("[START PARAGRAPH]")
        paragraph_frames, end = write_paragraph_to_image(paragraph, img, 
                                                             (x, y), width_box, 
                                                             comment_font, color)
        print("[END   PARAGRAPH]")

        frames = frames + paragraph_frames
        x, y = pos[0], end[1] + int(line_spacing * 1.2)
    print("[END   WRITE COMMENT]")
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
        n, s = time_ago // 2678400, 'month'
    elif time_ago > 604800:
        n, s = time_ago // 604800, 'week'
    elif time_ago > 86400:
        n, s = time_ago // 86400, 'day'
    elif time_ago > 3600:
        n, s = time_ago // 3600, 'hour'
    elif time_ago > 60:
        n, s = time_ago // 60, 'minute'
    else:
        n, s = time, 'second'
    if n > 1:
        s += 's'
    return str(n) + ' ' + s + ' ago'




def draw_comment_header_to_image(img, pos, 
                                 username, npoints, created_utc, medals):
    draw  = ImageDraw.Draw(img)
    text_color = (255, 255, 255, 1)
    username_color = (22, 210, 252, 1)

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
    x, y = pos
    img.paste(footer_img, (x, y), footer_img)
    return (x, y + footer_padding)




def create_comment_frames(comment, img, start):

    end = (text_width_cutoff, text_height_cutoff)
    color = (255, 255, 255, 1)

    x, y = start

    sidebar_pos = x + sidebar_offset[0], y + sidebar_offset[1]
    line_height = compute_line_height(comment, (x, text_width_cutoff))
    print(line_height)
    draw_comment_sidebar_to_image(img, sidebar_pos, line_height)

    header_pos = x + header_offset[0], y + header_offset[1]
    draw_comment_header_to_image(img, header_pos, comment['author'], comment['score'], 
                                 comment['created_utc'], '')

    frames, (x, y) = write_comment_to_image(comment['body'], img, (x, y), end)

    comment_end_padding = 0
    y += comment_end_padding

    # draw comment footer to last frame
    footer_pos  = x + footer_offset[0], y + footer_offset[1]
    (x, y) = draw_comment_footer_to_image(img, (x, y))
    frames[-1] = np.array(img)
    return frames, img, (x, y)




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
    paragraphs = get_paragraphs(comment_body)
    for paragraph in paragraphs:
        sentences = get_sentences(paragraph)
        for sentence in sentences:
            file_name = 'audio' + str(n) + '.mp3'
            audio_file_names.append(os.path.join(temp_dir, file_name))
            durations.append(create_audio_file(sentence, file_name))
            n += 1
    audio = AudioSegment.from_file(audio_file_names[0], format='mp3')
    for file_name in audio_file_names[1:]:
        audio += AudioSegment.from_file(file_name, format='mp3')
    audio.export(os.path.join(temp_dir, audio_name))
    return durations



# creates audio for each sentence of the comment body with gTTs and combines
# them into one long mp3 file 
#
# creates a video that displays each sentence as it is spoken and holds it 
# for the duration of its respective spoken duration from gTTS, with no audio
# 
# combines the audioless video and the audio with ffmpeg for a video of just this comment
# 
# returns the img given, in case this comment is part of a tree
def create_comment_video(comment, img, start, comment_n):
    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    out    = cv2.VideoWriter(os.path.join(temp_dir, na_video_name), fourcc, fps, (screen_width, screen_height))

    durations        = create_comment_audio(comment['body'])
    frames, img, end = create_comment_frames(comment, img, start)

    print(f"len(frames) = {len(frames)}\nlen(durations) = {len(durations)}")
    for frame, duration in list(zip(frames, durations)):
        cv2_frame = cv2.cvtColor(frame, cv2.COLOR_RGBA2BGR)
        for _ in range(fps * duration):
            out.write(cv2_frame)

    out.release()
    cv2.destroyAllWindows()

    comment_video_name = comment_video_name_base + str(comment_n) + '.mp4'
    subprocess.run(f"ffmpeg -i {temp_dir}{na_video_name} -i {temp_dir}{audio_name} -c copy -map 0:v:0 -map 1:a:0 ./{working_dir}{comment_video_name} > /dev/null 2>&1", shell=True, timeout=120)
    print(f"[VIDEO CREATED   ]: {comment_video_name}")
    return img, end, comment_video_name

def compute_comment_body_height(comment_body, width_box):
    x, y = 0, 0
    start_x, end_x = width_box
    end_padding = 25

    for sentence in get_sentences(comment_body):
        sent_width, sent_height, _ = get_text_size_freetype(sentence, comment_font)
        if x + sent_width > int(end_x * 0.9):
            lines = wrap_text(sentence, width_box, comment_font, (x, y))
        else:
            lines = [sentence]

        first_line_width = get_text_size_freetype(lines[0], comment_font)[0]
        if len(lines) == 1:
            x += first_line_width + end_padding
            continue;
        y += line_spacing

        for line in lines[1:-1]:
            y += line_spacing
        last_line_width = get_text_size_freetype(lines[-1], comment_font)[0]
        x = start_x + last_line_width + end_padding

    return y + line_spacing

def compute_total_comment_height(comment_body, width_box):
    body_height = compute_comment_body_height(comment_body, width_box)
    return header_font_height + header_offset[1]  + body_height + footer_offset[1] + footer_padding + comment_end_padding

def compute_line_height(comment, width_box):
    start_x0, end_x = width_box
    start_x1 = start_x0 + indentation_offset
    start_x2 = start_x1 + indentation_offset
    height = compute_comment_body_height(comment['body'], width_box)
    for reply1 in comment['replies']:
        height += compute_total_comment_height(reply1['body'], (start_x1, end_x))
        for reply2 in comment['replies']:
            height += compute_total_comment_height(reply2['body'], (start_x2, end_x))
    return height

# creates several subvideos and makes a call to ffmpeg to concatenate them
def create_comment_chain_video(comment, chain_n):

    img = Image.new("RGBA", (screen_width, screen_height), background_color)
    comment_n = 0
    file_names = []

    # TODO this is temporary. Must preprocess comment chain and compute total comment height
    # for each comment beforehand, and loop through the "comment structure" 
    # given by `comment` argument to the function, keeping track of 
    (x, y) = (text_start_x, text_start_y)
    img, end, file_name = create_comment_video(comment, img, (x, y), comment_n)
    comment_n += 1
    file_names.append(file_name)

    # TODO temporary read above
    (x, y) = end[0] + indentation_offset, end[1] + comment_end_padding
    img, end, file_name = create_comment_video(comment['replies'][0], img, (x, y), comment_n)
    comment_n += 1
    file_names.append(file_name)
    
    out_file_name = chain_video_name_base + str(chain_n) + '.mp4'

    with open(file_names_txt_file, 'w') as f:
        for file_name in file_names:
            f.write('file \'' + file_name + '\'\n')

    subprocess.run(f"ffmpeg -f concat -safe 0 -i {file_names_txt_file} -c copy ./{working_dir}{out_file_name} > /dev/null 2>&1", shell=True, timeout=120)

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
    #load_top_posts_and_best_comments('AmItheAsshole')

    with codecs.open('posts.json', 'r', 'utf-8') as posts_file:
        posts = json.load(posts_file)

    comment = posts[0]["comments"][0]
    comment['replies'] = [comment['replies'][0]]
    comment['replies'][0]['replies'] = []

    width_box = (text_start_x, text_width_cutoff)
    body_height  = compute_comment_body_height(comment['body'], width_box )
    total_height = compute_total_comment_height(comment['body'], width_box)
    line_height  = compute_line_height(comment, width_box)
    print(f"body_height: {body_height}, total_height: {total_height}, line_height: {line_height}")

    create_comment_chain_video(posts[0]["comments"][0], 1)
    #create_final_video(posts[0]["comments"][:2])



