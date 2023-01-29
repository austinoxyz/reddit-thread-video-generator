# automate-youtube.py

import praw
import json
import cv2
import numpy as np
import uuid
import os
import time
import textwrap
from gtts import gTTS
from pydub import AudioSegment
import subprocess

_cwd = "/home/anon/Videos/automate-yt/"

# OpenCV Image configuration parameters
height, width = 1080, 1920
fps, duration = 30, 30
font = cv2.FONT_HERSHEY_SIMPLEX
font_scale = 1.8
line_type = cv2.LINE_AA
thickness = 2

video_name         = 'video.mp4'
title_audio_name   = 'title.mp3'
audio_name         = 'post_audio.mp3'
final_video_name   = 'final.mp4'

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
    with open('posts.json', 'w') as json_file:
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

def create_post_images(title, content):
    return [create_title_image(title)] + create_content_images(content)

def create_title_image(title):
    img = np.full((height, width, 3), (255, 255, 255), np.uint8)
    text_size, _ = cv2.getTextSize(title, font, font_scale, thickness)
    if text_size[0] > width:
        lines = wrap_text(title, width, font, font_scale, thickness)
    else:
        lines = [title]
    
    y = int(height * 0.1)
    for line in lines:
        text_width, text_height = cv2.getTextSize(line, font, font_scale, thickness)[0]
        x = int((width - text_width) / 2)
        cv2.putText(img, line, (x, y), font, font_scale, (0, 0, 255), thickness=1, lineType=line_type)
        y += text_height + 10
    return img

def create_content_images(content):
    content_sentences = content.split(".")
    sentence_pairs = [content_sentences[i:i+2] for i in range(0, len(content_sentences), 2)]
    content_images = []
    for sentence_pair in sentence_pairs:
        content_images.append(create_content_image(sentence_pair))
    return content_images

def create_content_image(sentences):
    img = np.full((height, width, 3), (255, 255, 255), np.uint8)
    text = '\n'.join(sentences)
    text_size, _ = cv2.getTextSize(text, font, font_scale, thickness)
    if text_size[0] > width:
        lines = wrap_text(text, width, font, font_scale, thickness)
    else:
        lines = [text]

    y = int(height * 0.1)
    for line in lines:
        text_width, text_height = cv2.getTextSize(line, font, font_scale, thickness)[0]
        x = int((width - text_width) / 2)
        cv2.putText(img, line, (x, y), font, font_scale, (0, 0, 255), thickness=thickness, lineType=line_type)
        y += text_height + 10
    return img

def create_audio_files(title, content):
    durations = [create_title_audio(title)] + create_content_audio(content)

    content_audio_file_names = [os.path.join(_cwd, 'content' + str(i + 1) + '.mp3') 
                                for i in range(len(durations) - 1)]
    audio_file_names = [os.path.join(_cwd, title_audio_name)] + content_audio_file_names
    audio = AudioSegment.from_file(audio_file_names[0], format='mp3')
    for file_name in audio_file_names[1:]:
        audio += AudioSegment.from_file(file_name, format='mp3')
    audio.export(os.path.join(_cwd, audio_name))

    return durations

def create_title_audio(title):
    tts = gTTS(text=title, lang='en')
    tts.save(os.path.join(_cwd, title_audio_name))
    audio = AudioSegment.from_file(os.path.join(_cwd, title_audio_name), format='mp3')
    duration = audio.duration_seconds
    del audio
    return int(duration)

def create_content_audio(content):
    content_sentences = content.split(".")
    sentence_pairs = [content_sentences[i:i+2] for i in range(0, len(content_sentences), 2)]
    durations = []
    for n, sentence_pair in enumerate(sentence_pairs):
        text = '\n'.join(sentence_pair)
        tts = gTTS(text=text, lang='en')
        file_name = 'content' + str(n + 1) + '.mp3'
        tts.save(os.path.join(_cwd, file_name))
        audio = AudioSegment.from_file(os.path.join(_cwd, 'content' + str(n + 1) + '.mp3'), format='mp3')
        durations.append(int(audio.duration_seconds))
        del audio
    return durations

def create_video(post):
    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    out = cv2.VideoWriter(os.path.join(_cwd, video_name), fourcc, fps, (width, height))

    title = post['title']
    content = post['content']

    images    = create_post_images(title, content)
    durations = create_audio_files(title, content)

    for img, duration in list(zip(images, durations)):
        for _ in range(int(fps * duration * 1.055)):
            out.write(img)
    out.release()

    subprocess.run(f"ffmpeg -i {video_name} -i {audio_name} -c copy -map 0:v:0 -map 1:a:0 {final_video_name}", shell=True, cwd=_cwd, timeout=120)


if __name__ == '__main__':

    #    load_posts('AmItheAsshole')

    with open('posts.json', 'r') as posts_file:
        posts = json.load(posts_file)

    create_video(posts[5])


