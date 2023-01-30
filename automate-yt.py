# automate-youtube.py

import praw
from praw.models import Redditor, Comment, MoreComments
import json
import cv2
import numpy as np
import uuid
import os
import re
import time
import textwrap
import codecs
from gtts import gTTS
from pydub import AudioSegment
import subprocess
from PIL import Image, ImageDraw, ImageFont

_cwd = "/home/anon/Videos/automate-yt/"

height, width = 1080, 1920 
aspect = float(width / height)
fps = 30
background_color = (90, 90, 90, 0)

text_width_cutoff = width * 0.90
text_start_x  = width - text_width_cutoff

text_height_cutoff = height * 0.90
text_start_y  = height - text_height_cutoff

title_font_path = os.path.join("/usr/share/fonts/truetype", "noto/NotoSansMono-Bold.ttf")
title_font_size = 92
title_font = ImageFont.truetype(title_font_path, title_font_size)

content_font_path = os.path.join("/usr/share/fonts/truetype", "dejavu/DejaVuSerif.ttf")
content_font_size = 20
content_font = ImageFont.truetype(content_font_path, content_font_size)
content_font_color = (255, 255, 255)

audio_file_names = []

video_name         = 'video.mp4'
title_audio_name   = 'title.mp3'
audio_name         = 'post_audio.mp3'
final_video_name   = 'final.mp4'

# for syncing each audio file to its respective frame
magic_audio_constant = 1.083

acronym_map = {
    'AITA': 'am i the asshole',        'aita': 'am i the asshole',
    'OP': 'oh pee',                    'op': 'oh pee',
    'IIRC': 'if i recall correctly',   'iirc': 'if i recall correctly',
    'AFAIK': 'as far as i know',       'afaik': 'as far as i know',
    'DAE': 'does anyone else',         'dae': 'does anyone else',
    'ICYMI': 'in case you missed it',  'icymi': 'in case you missed it',
    'tldr': 'too long didnt read',     'TL;DR': 'too long didnt read',
    'TIL': 'today i learned',          'til': 'today i learned',
    'IDK': 'i dont know',              'idk': 'i dont know',
    'LPT': 'life pro tip',             'lpt': 'life pro tip',
}

def load_posts(subreddit_name):
    reddit = praw.Reddit(client_id=    'Sx5GE4fYzUuNLwEg_h8k4w',
                         client_secret='0n4qkZVolBDeR2v5qq6-BnSuJyhQ7w',
                         user_agent=   'python-script')
    subreddit = reddit.subreddit(subreddit_name)
    posts = subreddit.top(limit=10, time_filter='all')
    post_data = []
    for post in posts:
        post_data.append({
            'title': post.title,
            'score': post.score,
            'url': post.url,
            'author': post.author.name,
            'content': post.selftext
        })
    with codecs.open('posts.json', 'w', 'utf-8') as json_file:
        json.dump(post_data, json_file)

def load_posts_with_comments(subreddit_name):
    reddit = praw.Reddit(client_id=    'Sx5GE4fYzUuNLwEg_h8k4w',
                         client_secret='0n4qkZVolBDeR2v5qq6-BnSuJyhQ7w',
                         user_agent=   'python-script')
    subreddit = reddit.subreddit(subreddit_name)
    posts = subreddit.top(limit=10, time_filter='all')
    post_data = []
    for post in posts:
        comments = [comment for comment in post.comments.list() 
                    if not isinstance(comment, MoreComments)]
        comments.sort(key=lambda x: x.score, reverse=True)
        top_comments = comments[:10]
        comments_data = []
        for comment in top_comments:
            # not sure why this is happening to the last comment in the list
            if comment.author is None:
                continue
            print(comment.author.name)
            subcomments = [subcomment for subcomment in comment.replies.list() 
                        if not isinstance(subcomment, MoreComments)]
            subcomments.sort(key=lambda x: x.score, reverse=True)
            top_subcomments = subcomments[:3]
            subcomments_data = []
            for subcomment in top_subcomments:
                # not sure why this is happening to the last comment in the list
                if subcomment.author is None:
                    continue
                print(subcomment.author.name)
                subcomments_data.append({
                    'author': subcomment.author.name,
                    'score':  subcomment.score,
                    'permalink': subcomment.permalink,
                    'body':   subcomment.body,
                    'time_posted': subcomment.created_utc,
                    'id': subcomment.id
                })

            comments_data.append({
                'author': comment.author.name,
                'score':  comment.score,
                'permalink': comment.permalink,
                'body':   comment.body,
                'time_posted': comment.created_utc,
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

def get_text_size(font, text):
    bbox = font.getbbox(text)
    return (bbox[2] - bbox[0], bbox[3] - bbox[1])

title_font_height   = get_text_size(title_font, 'example_word')[1]
content_font_height = get_text_size(content_font, 'example_word')[1]

def get_paragraphs(content):
    return [s for s in re.split("(\n)+", content) if len(s) > 0]

def get_sentences(content):
    return [s + '. ' for s in re.split("[!?.]", content) if len(s) > 0]

def replace_acronyms(text):
    words = re.findall(r'\b\w+\b', text)
    pattern = r'\b(' + '|'.join(acronym_map.keys()) + r')\b'
    return re.sub(pattern, lambda x: acronym_map[x.group()], text)

def strip_newlines(text):
    return text.replace('\n', '')

def strip_excess_newlines(text):
    pattern = r'(\n)+'
    return re.sub(pattern, '\n', text)

def cleanup_text_for_video(text):
    text = text.replace('’', '\'')
    return text

def cleanup_text_for_audio(text):
    text = replace_acronyms(text)
    text = text.replace('’', '\'') # why reddit???
    return text



def create_audio_file(text, file_name):
    path = os.path.join(_cwd, file_name)
    text = cleanup_text_for_audio(text)
    tts = gTTS(text=text, lang='en')
    tts.save(os.path.join(_cwd, file_name))
    audio = AudioSegment.from_file(path, format='mp3')
    duration = audio.duration_seconds
    del audio
    return int(duration)



def wrap_text(text, max_width, font, starting_x):

    wrapped_text = []
    line = ''
    have_processed_first_line = False
    words = text.split(' ')

    for word in words:
        text_width, text_height = get_text_size(font, line + ' ' + word)

        if starting_x + text_width < max_width:
            line += ' ' + word
        else:
            if not have_processed_first_line:
                have_processed_first_line = True
                starting_x = text_start_x
            wrapped_text.append(line)
            line = word

    wrapped_text.append(line)
    return wrapped_text





# only contains the text within a specified width - 
# text will continue to grow downward in write_paragraph_to_image()
# so long as there are still sentences to write in the paragraph
def write_text_to_image(text, font, spacing, color, img, pos, max_width):
    draw = ImageDraw.Draw(img)
    text_width, text_height = get_text_size(font, text)

    if pos[0] + text_width > int(max_width * 0.9):
        lines = wrap_text(text, max_width, font, pos[0])
    else:
        lines = [text]

    x, y = pos
    last_y = y
    
    if lines[0] == '':
        x = pos[0]
        y += spacing

    for n, line in enumerate(lines):
        if n == 0:
            draw.text((x, y), line, fill=color, font=font)
        else:
            draw.text((text_start_x, y), line, fill=color, font=font)
        line_width, line_height = get_text_size(font, line)
        last_y = y

        y += spacing
        x = pos[0] + line_width
    return img, (x, last_y)



def draw_comment_sidebar_to_image(img, pos):
    # comment sidebar contains: 
    #       upvote/downvote icons
    #       line going southward that runs off the screen (for comment tree)

    x, y = int(pos[0] - 50), int(pos[1])

    # load the upvote image, resize, and draw
    upvote_img  = Image.open('./res/upvote.png').convert("RGBA")
    upvote_size = (int(upvote_img.width / 5), int(upvote_img.height / 5))
    upvote_img  = upvote_img.resize(upvote_size)
    upvote_pos  = (x, y - 20)
    img.paste(upvote_img, upvote_pos, upvote_img)

    # load the downvote image, resize, and draw
    downvote_img  = Image.open('./res/downvote.png').convert("RGBA")
    downvote_size = (int(downvote_img.width / 5), int(downvote_img.height / 5))
    downvote_img  = downvote_img.resize(downvote_size)
    downvote_pos  = (x, y + 40)
    img.paste(downvote_img, downvote_pos, downvote_img)

    # draw the indentation line
    draw = ImageDraw.Draw(img)
    line_color = (200, 200, 200, 1)
    x_offset = upvote_size[0] / 2
    line_start, line_end = (x + x_offset, y + 100), (x + x_offset, height)
    draw.line([line_start, line_end], fill=line_color, width=5)

    return img

def points_str(npoints):
    multiplier = ''
    if npoints >= 1000000:
        npoints = npoints // 100000
        multiplier = 'm'
    elif npoints >= 1000:
        npoints = npoints // 1000
        multiplier = 'k'
    return str(npoints)[:-1] + '.' + str(npoints)[-1] + multiplier + ' points'

def time_ago_str(time_ago):
    return ''


def draw_comment_header_to_image(img, pos, username, npoints, time_ago, medals):
    # comment header contains: 
    #       username
    #       points
    #       time posted ago
    #       time edited ago (if applicable)
    #       medals (if applicable)

    x_padding = 10
    draw  = ImageDraw.Draw(img)
    color = (255, 255, 255, 1)
    font  = content_font
    font_height = get_text_size(font, 'A')[1]

    x, y = pos[0], pos[1] - font_height - 50

    # write the username above the image
    username = '/u/' + username
    username_length = get_text_size(font, username)[0]
    username_color = (0, 255, 0, 1)
    draw.text((x, y), username, fill=username_color, font=font)
    x += username_length + x_padding

    # write the username above the image

    points = points_str(npoints)
    points_length = get_text_size(font, points)[0]
    draw.text((x, y), points, fill=color, font=font)
    x += points_length + x_padding

    return False

def draw_comment_footer_to_image(img, pos):
    # comment header contains: 
    #       "Reply"
    #       "Give Award"
    #       "Share"
    #       "Report"
    #       "Save"
    return False

def write_paragraph_to_image(paragraph, img, pos, max_dimensions, font, spacing, font_color):
    x, y  = pos
    max_x, max_y = max_dimensions
    images = []
    draw = ImageDraw.Draw(img)
    sentences = get_sentences(paragraph)
    for sentence in sentences:
        img, (x, y) = write_text_to_image(sentence, font, spacing, font_color,
                                          img, (x, y), max_x)
        images.append(np.array(img))
        if x >= max_x * 0.8:
            x, y = pos[0], y + spacing
    return images, (x, y)

def write_comment_to_image(text, img, pos, max_dimensions, font, spacing, font_color):
    x, y = pos
    max_x, max_y = max_dimensions
    paragraphs = get_paragraphs(text)
    images = []
    for paragraph in paragraphs:
        paragraph_images, end_pos = write_paragraph_to_image(paragraph, img, (x, y), max_dimensions,
                                                            font, spacing, font_color)
        images = images + paragraph_images
        x, y = pos[0], end_pos[1] + (2 * spacing)
    return images, (x, y)

def create_comment_audio(comment):
    durations, audio_file_names, n = [], [], 1
    paragraphs = get_paragraphs(comment)
    for paragraph in paragraphs:
        sentences = get_sentences(paragraph)
        for sentence in sentences:
            file_name = 'audio' + str(n) + '.mp3'
            audio_file_names.append(os.path.join(_cwd, file_name))
            durations.append(create_audio_file(sentence, file_name))
            n += 1
    audio = AudioSegment.from_file(audio_file_names[0], format='mp3')
    for file_name in audio_file_names[1:]:
        audio += AudioSegment.from_file(file_name, format='mp3')
    audio.export(os.path.join(_cwd, audio_name))
    return durations


def create_comment_slides(comment):
    img = Image.new("RGBA", (width, height), background_color)

    start = (text_start_x, text_start_y)
    end = (text_width_cutoff, text_height_cutoff)
    spacing = int(content_font_height * 1)
    color = (255, 255, 255, 1)

    draw_comment_sidebar_to_image(img, start)
    draw_comment_header_to_image(img, start, 'test_user', 12853, '', '')

    images, comment_end = write_comment_to_image(comment, img, start, end, 
                                    content_font, spacing, color)
    draw_comment_footer_to_image(img, comment_end)
    return images


def create_comment_video(comment):
    comment = strip_newlines(comment) 
    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    out    = cv2.VideoWriter(os.path.join(_cwd, video_name), fourcc, fps, (width, height))

    durations = create_comment_audio(comment)
    images    = create_comment_slides(comment)

    cv2_images = [cv2.cvtColor(img, cv2.COLOR_RGBA2BGR) for img in images]

    for img, duration in list(zip(cv2_images, durations)):
        for _ in range(int(fps * duration * magic_audio_constant)):
            out.write(img)


    out.release()
    cv2.destroyAllWindows()
    subprocess.run(f"ffmpeg -i {video_name} -i {audio_name} -c copy -map 0:v:0 -map 1:a:0 {final_video_name}", shell=True, cwd=_cwd, timeout=120)





if __name__ == '__main__':
    load_posts_with_comments('AmItheAsshole')
    with codecs.open('posts.json', 'r', 'utf-8') as posts_file:
        posts = json.load(posts_file)
    create_comment_video(posts[5]["content"])




# def create_content_audio_files(content):
#     paragraphs = get_paragraphs(content)
#     durations = []
#     n = 1
#     for paragraph in paragraphs:
#         sentences = get_sentences(paragraph)
#         for sentence in sentences:
#             file_name = 'audio' + str(n) + '.mp3'
#             durations.append(create_audio_file(sentence, file_name))
#             n += 1
#     return durations
# 
# 
# 
# 
# def create_slides(title, content):
#     title_slide    = create_title_slide(title)
#     content_slides = create_content_slides(content)
#     return [title_slide] + content_slides
# 
# 
# 
# 
# def create_title_slide(title):
#     img = Image.new("RGB", (width, height), background_color)
# 
#     spacing = title_font_height + 20
#     color = (255, 255, 255)
#     img, _ = write_text_to_image(title, title_font, spacing, color,
#                                  img, (0.2*width, 0.2*height), text_width_cutoff)
#     return np.array(img)
# 
# 
# 
# def create_content_slides(text):
#     x, y = (text_start_x, text_start_y)
#     img = Image.new("RGB", (width, height), background_color)
#     paragraphs = get_paragraphs(text)
#     images = []
#     for paragraph in paragraphs:
#         sentences = get_sentences(paragraph)
#         for sentence in sentences:
#             spacing = int(content_font_height * 1)
#             img, (x, y) = write_text_to_image(sentence, content_font, spacing, 
#                                               content_font_color,
#                                               img, (x, y), text_width_cutoff)
#             images.append(np.array(img))
# 
# 
#             if x >= text_width_cutoff*0.8:
#                 x, y = text_start_x, y + spacing
# 
#             if y >= text_height_cutoff*0.8:
#                 img = Image.new("RGB", (width, height), background_color)
#                 x, y = text_start_x, text_start_y
#     return images
# 
# 
# 
# 
# 
# def create_audio(title, content):
#     durations = [create_audio_file(title, 'title.mp3')] + create_content_audio_files(content)
#     content_audio_file_names = [os.path.join(_cwd, 'audio' + str(i + 1) + '.mp3') 
#                                 for i in range(len(durations) - 1)]
#     audio_file_names = [os.path.join(_cwd, title_audio_name)] + content_audio_file_names
#     audio = AudioSegment.from_file(audio_file_names[0], format='mp3')
#     for file_name in audio_file_names[1:]:
#         audio += AudioSegment.from_file(file_name, format='mp3')
#     audio.export(os.path.join(_cwd, audio_name))
#     return durations
# 
# 
# 
# 
# def create_video(post):
#     fourcc = cv2.VideoWriter_fourcc(*"mp4v")
#     out = cv2.VideoWriter(os.path.join(_cwd, video_name), fourcc, fps, (width, height))
# 
#     title   = strip_newlines(post['title']) 
#     content = strip_newlines(post['content'])   
#     
#     durations = create_audio(title, content)
#     images    = create_slides(title, content)
# 
#     for img, duration in list(zip(images, durations)):
#         for _ in range(int(fps * duration * magic_audio_constant)):
#             out.write(img)
# 
#     out.release()
#     cv2.destroyAllWindows()
# 
#     subprocess.run(f"ffmpeg -i {video_name} -i {audio_name} -c copy -map 0:v:0 -map 1:a:0 {final_video_name}", shell=True, cwd=_cwd, timeout=120)


