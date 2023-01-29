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

_cwd = "/home/anon/Videos/automate-yt/"

# OpenCV Image configuration parameters
height, width = 1080, 1920
fps = 30

title_font = cv2.FONT_HERSHEY_SIMPLEX
title_font_scale = 3
title_thickness = 5

content_font = cv2.FONT_HERSHEY_SIMPLEX
content_font_scale = 2
content_thickness = 1

line_type = cv2.LINE_AA

video_name         = 'video.mp4'
title_audio_name   = 'title.mp3'
audio_name         = 'post_audio.mp3'
final_video_name   = 'final.mp4'

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

def wrap_text(text, width, font, font_scale, thickness):
    (text_width, text_height), _ = cv2.getTextSize(text, font, font_scale, thickness)
    wrapped_text = []
    line = ""
    for word in text.split(' '):
        if cv2.getTextSize(line + " " + word, font, font_scale, thickness)[0][0] < (width-60):
            line += " " + word
        else:
            wrapped_text.append(line)
            line = word
    wrapped_text.append(line)
    return wrapped_text

def get_sentence_pairs(content):
    content_sentences = [s + '.  ' for s in re.split("[!?.]", content) if len(s) > 0]
    return [content_sentences[i:i+2] for i in range(0, len(content_sentences), 2)]

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

def create_image(text, font, font_scale, thickness):
    text = cleanup_text_for_video(text)
    img = np.full((height, width, 3), (255, 255, 255), np.uint8)
    text_size, _ = cv2.getTextSize(text, font, font_scale, thickness)

    if text_size[0] > width:
        lines = wrap_text(text, width, font, font_scale, thickness)
    else:
        lines = [text]
    
    y = int(height * 0.1)
    for line in lines:
        # TODO replace this call with a PIL ImageDraw call so a custom .ttf font can be used
        text_width, text_height = cv2.getTextSize(line, font, font_scale, thickness)[0]
        x = int((width - text_width) / 2)
        line.encode('utf-8')
        cv2.putText(img, line, (x, y), font, font_scale, (0, 0, 255), thickness=1, lineType=line_type)
        y += text_height + 10
    return img

def create_content_images(content):
    content = cleanup_text_for_video(content)
    sentence_pairs = get_sentence_pairs(content)
    content_images = []
    for sentence_pair in sentence_pairs:
        text = ''.join(sentence_pair)
        content_images.append(create_image(text, content_font, content_font_scale, content_thickness))
    return content_images

def create_post_images(title, content):
    content_images = create_content_images(content)
    title_image    = create_image(title, title_font, title_font_scale, title_thickness)
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
        for _ in range(int(fps * duration * 1.038)):
            out.write(img)
    out.release()

    subprocess.run(f"ffmpeg -i {video_name} -i {audio_name} -c copy -map 0:v:0 -map 1:a:0 {final_video_name}", shell=True, cwd=_cwd, timeout=120)


if __name__ == '__main__':
    with codecs.open('posts.json', 'r', 'utf-8') as posts_file:
        posts = json.load(posts_file)
    create_video(posts[5])


