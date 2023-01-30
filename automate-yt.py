# automate-youtube.py

import praw
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
fps = 30
background_color = (255, 255, 255)

text_width_cutoff = width * 0.90
text_start_x  = width - text_width_cutoff

text_height_cutoff = height * 0.90
text_start_y  = height - text_height_cutoff

title_font_path = os.path.join("/usr/share/fonts/truetype", "noto/NotoSansMono-Bold.ttf")
title_font_size = 92
title_font = ImageFont.truetype(title_font_path, title_font_size)

content_font_path = os.path.join("/usr/share/fonts/truetype", "dejavu/DejaVuSerif.ttf")
content_font_size = 48
content_font = ImageFont.truetype(content_font_path, content_font_size)

audio_file_names = []

video_name         = 'video.mp4'
title_audio_name   = 'title.mp3'
audio_name         = 'post_audio.mp3'
final_video_name   = 'final.mp4'

# for syncing each audio file to its respective frame
magic_audio_constant = 1.049
magic_spacing_constant = 110

acronym_map = {
    'AITA': 'am i the asshole', 'aita': 'am i the asshole',
    'OP': 'oh pee', 'op': 'oh pee',
    'IIRC': 'if i recall correctly', 'iirc': 'if i recall correctly',
    'AFAIK': 'as far as i know', 'afaik': 'as far as i know',
    'DAE': 'does anyone else', 'dae': 'does anyone else',
    'ICYMI': 'in case you missed it', 'icymi': 'in case you missed it',
    'tldr': 'too long didnt read', 'TL;DR': 'too long didnt read',
    'TIL': 'today i learned', 'til': 'today i learned',
    'IDK': 'i dont know', 'idk': 'i dont know',
    'LPT': 'life pro tip', 'lpt': 'life pro tip',
}

def load_posts(subreddit_name):
    reddit = praw.Reddit(client_id='Sx5GE4fYzUuNLwEg_h8k4w',
                         client_secret='0n4qkZVolBDeR2v5qq6-BnSuJyhQ7w',
                         user_agent='python-script')
    subreddit = reddit.subreddit(subreddit_name)
    posts = subreddit.top(limit=10, time_filter='all')
    data = []
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

def get_text_size(font, text):
    bbox = font.getbbox(text)
    return (bbox[2] - bbox[0], bbox[3] - bbox[1])

def wrap_text(text, max_width, font):
    wrapped_text = []
    line = ''
    for word in text.split(' '):
        text_width, text_height = get_text_size(font, line + ' ' + word)
        if text_width < max_width:
            line += ' ' + word
        else:
            wrapped_text.append(line)
            line = word
    wrapped_text.append(line)
    return wrapped_text

def get_paragraphs(content):
    return [s for s in re.split("(\n)+", content) if len(s) > 0]

def get_sentences(content):
    return [s + '. ' for s in re.split("[!?.]", content) if len(s) > 0]

def get_sentence_pairs(content):
    sentences = get_sentences(content)
    return [sentences[i:i+2] for i in range(0, len(sentences), 2)]

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


# video and audio functionality beneath this comment

def create_image(text, font):
    text = cleanup_text_for_video(text)
    img = Image.new("RGB", (width, height), background_color)
    draw = ImageDraw.Draw(img)
    text_width, text_height = get_text_size(font, text)

    if text_width > width:
        lines = wrap_text(text, text_width_cutoff, font)
    else:
        lines = [text]
    
    y = int(height * 0.1)
    for line in lines:
        line_width, line_height = get_text_size(font, line)
        y += line_height + 10
        x = int((width - line_width) / 2)
        draw.text((x, y), line, fill=(0, 0, 0), font=font)
    return np.array(img)



def create_content_images(content):
    content = cleanup_text_for_video(content)
    sentence_pairs = get_sentence_pairs(content)
    content_images = []
    for sentence_pair in sentence_pairs:
        text = ''.join(sentence_pair)
        content_images.append(create_image(text, content_font))
    return content_images



def create_post_images(title, content):
    title   = cleanup_text_for_video(title)
    content = cleanup_text_for_video(content)
    title_image    = create_image(title, title_font)
    content_images = create_content_images(content)
    return [title_image] + content_images



def create_audio_file(text, file_name):
    path = os.path.join(_cwd, file_name)
    text = cleanup_text_for_audio(text)
    tts = gTTS(text=text, lang='en')
    tts.save(os.path.join(_cwd, file_name))
    audio = AudioSegment.from_file(path, format='mp3')
    duration = audio.duration_seconds
    del audio
    return int(duration)



def create_content_audio_files(content):
    sentence_pairs = get_sentence_pairs(content)
    durations = []
    for n, sentence_pair in enumerate(sentence_pairs):
        text = ''.join(sentence_pair)
        file_name = 'content' + str(n + 1) + '.mp3'
        durations.append(create_audio_file(text, file_name))
    return durations



def create_audio_files(title, content):
    title_audio_duration = create_audio_file(title, 'title.mp3')
    content_audio_durations = create_content_audio_files(content)
    durations = [title_audio_duration] + content_audio_durations

    content_audio_file_names = [os.path.join(_cwd, 'content' + str(i + 1) + '.mp3') 
                                for i in range(len(durations) - 1)]
    audio_file_names = [os.path.join(_cwd, title_audio_name)] + content_audio_file_names

    audio = AudioSegment.from_file(audio_file_names[0], format='mp3')
    for file_name in audio_file_names[1:]:
        audio += AudioSegment.from_file(file_name, format='mp3')
    audio.export(os.path.join(_cwd, audio_name))
    return durations



def create_video(post):
    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    out = cv2.VideoWriter(os.path.join(_cwd, video_name), fourcc, fps, (width, height))

    title = strip_newlines(post['title']) 
    content = strip_newlines(post['content'])

    print(title)
    print(content)

    images    = create_post_images(title, content)
    durations = create_audio_files(title, content)

    for img, duration in list(zip(images, durations)):
        for _ in range(int(fps * duration * magic_audio_constant)):
            out.write(img)

    out.release()
    cv2.destroyAllWindows()
    subprocess.run(f"ffmpeg -i {video_name} -i {audio_name} -c copy -map 0:v:0 -map 1:a:0 {final_video_name}", shell=True, cwd=_cwd, timeout=120)



def wrap_text2(text, max_width, font, starting_x):
    wrapped_text = []
    line = ''
    have_processed_first_line = False
    for word in text.split(' '):
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





# img is PIL.Image
def write_text_to_image(text, font, img, pos):
    draw = ImageDraw.Draw(img)
    text_width, text_height = get_text_size(font, text)

    if pos[0] + text_width > width:
        lines = wrap_text2(text, text_width_cutoff, font, pos[0])
    else:
        lines = [text]
    
    x, y = pos
    last_y = y
    for n, line in enumerate(lines):
        if n == 0:
            draw.text((x, y), line, fill=(0, 0, 0), font=font)
        else:
            draw.text((text_start_x, y), line, fill=(0, 0, 0), font=font)
        line_width, line_height = get_text_size(font, line)
        last_y = y

        y += line_height + magic_spacing_constant
        x = text_start_x + line_width
    return img, (x, last_y)



def create_content_audio_files2(content):
    paragraphs = get_paragraphs(content)
    durations = []
    n = 1
    for paragraph in paragraphs:
        sentences = get_sentences(paragraph)
        for sentence in sentences:
            file_name = 'audio' + str(n) + '.mp3'
            durations.append(create_audio_file(sentence, file_name))
            n += 1
    return durations



def create_slides(title, content):
    title_slide    = create_title_slide(title)
    content_slides = create_content_slides(content)
    return [title_slide] + content_slides



def create_title_slide(title):
    img = Image.new("RGB", (width, height), background_color)
    img, _ = write_text_to_image(title, title_font, img, pos=(0.2*width, 0.2*height))
    return np.array(img)



def create_content_slides(text):
    x, y = (text_start_x, text_start_y)
    img = Image.new("RGB", (width, height), background_color)
    paragraphs = get_paragraphs(text)
    images = []
    for paragraph in paragraphs:
        sentences = get_sentences(paragraph)
        for sentence in sentences:
            img, (x, y) = write_text_to_image(sentence, content_font, img, pos=(x, y))
            images.append(np.array(img))
            if y >= text_height_cutoff:
                img = Image.new("RGB", (width, height), background_color)
                x, y = text_start_x, text_start_y
    return images




def create_audio2(title, content):
    durations = [create_audio_file(title, 'title.mp3')] + create_content_audio_files2(content)
    content_audio_file_names = [os.path.join(_cwd, 'audio' + str(i + 1) + '.mp3') 
                                for i in range(len(durations) - 1)]
    audio_file_names = [os.path.join(_cwd, title_audio_name)] + content_audio_file_names
    audio = AudioSegment.from_file(audio_file_names[0], format='mp3')
    for file_name in audio_file_names[1:]:
        audio += AudioSegment.from_file(file_name, format='mp3')
    audio.export(os.path.join(_cwd, audio_name))
    return durations



def create_video2(post):
    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    out = cv2.VideoWriter(os.path.join(_cwd, video_name), fourcc, fps, (width, height))

    title   = strip_newlines(post['title']) 
    content = strip_newlines(post['content'])   
    
    durations = create_audio2(title, content)
    images    = create_slides(title, content)

    for img, duration in list(zip(images, durations)):
        for _ in range(int(fps * duration * magic_audio_constant)):
            out.write(img)

    out.release()
    cv2.destroyAllWindows()

    subprocess.run(f"ffmpeg -i {video_name} -i {audio_name} -c copy -map 0:v:0 -map 1:a:0 {final_video_name}", shell=True, cwd=_cwd, timeout=120)



if __name__ == '__main__':
    with codecs.open('posts.json', 'r', 'utf-8') as posts_file:
        posts = json.load(posts_file)
    create_video2(posts[5])


