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
font, font_scale = cv2.FONT_HERSHEY_SIMPLEX, 1.8
line_type = cv2.LINE_AA

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

def wrap_text(text, width, font, font_scale, line_type):
    (text_width, text_height), _ = cv2.getTextSize(text, font, font_scale, line_type)
    wrapped_text = []
    line = ""
    for word in text.split(' '):
        if cv2.getTextSize(line + " " + word, font, font_scale, line_type)[0][0] < (width-60):
            line += " " + word
        else:
            wrapped_text.append(line)
            line = word
    wrapped_text.append(line)
    return wrapped_text

def write_post_to_image(post, img):
    # draw the title text, with line wrapping
    post_size, _ = cv2.getTextSize(post['title'], font, font_scale, line_type)
    if post_size[0] > width:
        lines = wrap_text(post['title'], width, font, font_scale, line_type)
    else:
        lines = [post['title']]
    y = int(height * 0.1)
    for line in lines:
        text_width, text_height = cv2.getTextSize(line, font, font_scale, line_type)[0]
        x = int((width - text_width) / 2)
        cv2.putText(img, line, (x, y), font, font_scale, (0, 0, 255), thickness=1, lineType=line_type)
        y += text_height + 10

    # draw the content text beneath the title, with line wrapping
    content_size, _ = cv2.getTextSize(post['content'], font, font_scale, line_type)
    if content_size[0] > width:
        lines = wrap_text(post['content'], width, font, font_scale, line_type)
    else:
        lines = [post['content']]
    y = y + int(height * 0.1)
    for line in lines:
        text_width, text_height = cv2.getTextSize(line, font, font_scale, line_type)[0]
        x = int((width - text_width) / 2)
        cv2.putText(img, line, (x, y), font, font_scale, (0, 255, 0), thickness=1, lineType=line_type)
        y += text_height + 10

video_name         = 'video.mp4'
title_audio_name   = 'title.mp3'
content_audio_name = 'content.mp3'
audio_name         = 'post_audio.mp3'
final_video_name   = 'final.mp4'

def create_audio_files(title, content):
    tts = gTTS(text=title, lang='en')
    tts.save(os.path.join(_cwd, title_audio_name))
    tts = gTTS(text=content, lang='en')
    tts.save(os.path.join(_cwd, content_audio_name))

    title_audio   = AudioSegment.from_file(os.path.join(_cwd, title_audio_name),   format='mp3')
    content_audio = AudioSegment.from_file(os.path.join(_cwd, content_audio_name), format='mp3')

    audio = title_audio + content_audio
    audio.export(os.path.join(_cwd, audio_name), format='mp3')
    return int(audio.duration_seconds)

def create_video(post):
    img = np.full((height, width, 3), (255, 255, 255), np.uint8)
    write_post_to_image(post, img)
    audio_duration = create_audio_files(post['title'], post['content'])

    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    out = cv2.VideoWriter(os.path.join(_cwd, video_name), fourcc, fps, (width, height))
    for i in range(int(fps * audio_duration)):
        out.write(img)
    out.release()

    subprocess.run(f"ffmpeg -i concat:{title_audio_name}|{content_audio_name} -acodec pcm_s16le -ar 44100 {audio_name}", shell=True, cwd=_cwd, timeout=120)
    subprocess.run(f"ffmpeg -i {video_name} -i {audio_name} -c copy -map 0:v:0 -map 1:a:0 {final_video_name}", shell=True, cwd=_cwd, timeout=120)

if __name__ == '__main__':
    #    load_posts('AmItheAsshole')
    with open('posts.json', 'r') as posts_file:
        posts = json.load(posts_file)
    create_video(posts[5])



