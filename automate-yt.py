# automate-youtube.py

import os
import re
import time
import datetime
import textwrap
import codecs

import praw
import json
from praw.models import Redditor, Comment, MoreComments
from gtts import gTTS
from pydub import AudioSegment
from PIL import Image, ImageDraw, ImageFont
import numpy as np
import cv2
import subprocess

height, width = 1080, 1920 
aspect = float(width / height)
fps = 30
background_color = (26, 26, 27, 0)

text_width_cutoff = width * 0.96
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

#comment_font_path = os.path.join("/usr/share/fonts/truetype", "iosevka/iosevka.ttc")
comment_font_path = os.path.join("/usr/share/fonts/truetype", "noto/NotoSansMono-Bold.ttf")
comment_font_size = 24
comment_font = ImageFont.truetype(comment_font_path, comment_font_size)
comment_font_color = (255, 255, 255)

base_dir    = '/home/anon/Videos/automate-yt'
temp_dir    = base_dir + '/tmp'
video_name  = 'audioless_video.mp4'
audio_name  = 'audio.mp3'
working_dir = base_dir + '/working'
comment_video_name_base = 'comment'
final_video_name = 'final.mp4'

# for syncing each audio file to its respective frame
magic_audio_constant = 1.083

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

def load_top_posts_and_best_comments(subreddit_name):
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

def get_text_size(font, text):
    bbox = font.getbbox(text)
    return (bbox[2] - bbox[0], bbox[3] - bbox[1])

title_font_height   = get_text_size(title_font, 'example_word')[1]
content_font_height = get_text_size(content_font, 'example_word')[1]

def get_paragraphs(content):
    return [s for s in re.split("(\n)+", content) if len(s) > 0]

def get_sentences(content):
    return [s.strip() + '.' for s in re.split("[!?.]", content) if len(s) > 0]

def replace_acronyms(text):
    words = re.findall(r'\b\w+\b', text)
    pattern = r'\b(' + '|'.join(acronym_map.keys()) + r')\b'
    return re.sub(pattern, lambda x: acronym_map[x.group()], text)

def strip_newlines(text):
    return text.replace('\n', '')

def strip_excess_newlines(text):
    pattern = r'(\n)+'
    return re.sub(pattern, '\n', text)

def insert_spaces_after_sentences(paragraph):
    result = ''
    for i in range(len(paragraph)):
        char = paragraph[i]
        result += char
        if char == '.' and (i + 1 >= len(paragraph) or paragraph[i + 1] != ' '):
            result += ' '
    return result

def cleanup_paragraphs(paragraphs):
    # go through the list and join together all adjacent paragraphs 
    # that have two sentences or less.
    result = []
    joined_paragraph = ''
    for paragraph in paragraphs:
        sentences = get_sentences(paragraph)
        if len(sentences) < 2:
            joined_pargraph += paragraph
        else:
            result.append(joined_paragraph)
            result.append(paragraph)
    return [insert_spaces_after_sentences(p) for p in result if p != '']




def cleanup_text_for_video(text):
    text = text.replace('’', '\'')
    return text

def cleanup_text_for_audio(text):
    text = replace_acronyms(text)
    text = text.replace('’', '\'') # why reddit???
    return text



def create_audio_file(text, file_name):
    path = os.path.join(temp_dir, file_name)
    text = cleanup_text_for_audio(text)
    tts = gTTS(text=text, lang='en')
    tts.save(os.path.join(temp_dir, file_name))
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

    return [line for line in wrapped_text if line != '']





# only contains the text within a specified width - 
# text will continue to grow downward in write_paragraph_to_image()
# so long as there are still sentences to write in the paragraph
def write_sentence_to_image(text, img, 
                            pos, width_box, spacing, 
                            font, color):

    draw = ImageDraw.Draw(img)
    text_width, text_height = get_text_size(font, text)
    start_x, end_x = width_box

    if pos[0] + text_width > int(end_x * 0.9):
        lines = wrap_text(text, end_x - start_x, font, pos[0])
    else:
        lines = [text]

    x, y = pos
    last_y = y

    draw.text((x, y), lines[0], fill=color, font=font)
    line_width, line_height = get_text_size(font, lines[0])

    if len(lines) == 1:
        return img, (pos[0] + line_width, y)

    y += spacing

    for n, line in enumerate(lines[1:]):
        draw.text((start_x, y), line, fill=color, font=font)
        line_width, line_height = get_text_size(font, line)
        last_y = y
        y += spacing

    return img, (start_x + line_width, last_y)




def write_paragraph_to_image(paragraph, img, 
                             pos, width_box, spacing, 
                             font, color):
    x, y  = pos
    max_x, max_y = width_box
    images = []
    sentences = get_sentences(paragraph)
    print(sentences)
    for sentence in sentences:
        img, (x, y) = write_sentence_to_image(sentence, img, 
                                              (x, y), (pos[0], max_x), spacing, 
                                              font, color)
        images.append(np.array(img))
    return images, (x, y)




def write_comment_to_image(comment_body, img, 
                           pos, width_box, spacing):
    x, y = pos
    max_x, max_y = width_box
    color = (255, 255, 255, 1)
    paragraphs = get_paragraphs(comment_body)
    paragraphs = cleanup_paragraphs(paragraphs)
    images = []
    print(paragraphs)
    for paragraph in paragraphs:
        paragraph_images, end_pos = write_paragraph_to_image(paragraph, img, 
                                                             (x, y), width_box, spacing, 
                                                             comment_font, color)
        images = images + paragraph_images
        x, y = pos[0], end_pos[1] + (2 * spacing)
    return images, (x, y)





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
    font  = comment_font
    font_height = get_text_size(font, 'A')[1]

    x_padding = 10
    x, y = pos[0], pos[1] - font_height - 25

    # write the username above the image
    username = '/u/' + username
    username_length = get_text_size(font, username)[0]
    username_color = (22, 210, 252, 1)
    draw.text((x, y), username, fill=username_color, font=font)
    x += username_length + x_padding

    # write the points after the username 
    points = points_str(npoints)
    points_length = get_text_size(font, points)[0]
    draw.text((x, y), points, fill=text_color, font=font)
    x += points_length + x_padding

    # write the time duration since comment was posted
    time_ago = time_ago_str(created_utc)
    time_ago_length = get_text_size(font, time_ago)[0]
    draw.text((x, y), time_ago, fill=text_color, font=font)
    x += time_ago_length + x_padding



def draw_comment_sidebar_to_image(img, pos):
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
    line_color = (40, 40, 40, 1)
    x_offset = upvote_size[0] / 2
    line_start, line_end = (x + x_offset, y + 100), (x + x_offset, height)
    draw.line([line_start, line_end], fill=line_color, width=5)




def draw_comment_footer_to_image(img, pos):
    x, y = pos
    cf_img  = Image.open('./res/comment_footer.png').convert("RGBA")
    size = (int(cf_img.width / 2), int(cf_img.height / 2))
    cf_img  = cf_img.resize(size)
    pos  = (int(x), int(y) - 20) # huh? why need?
    img.paste(cf_img, pos, cf_img)




def create_comment_frames(comment, img, start):

    end = (text_width_cutoff, text_height_cutoff)
    spacing = get_text_size(comment_font, 'A')[1] * 1.7
    color = (255, 255, 255, 1)

    draw_comment_sidebar_to_image(img, start)
    draw_comment_header_to_image(img, start, comment['author'], comment['score'], 
                                 comment['created_utc'], '')

    frames, text_end = write_comment_to_image(comment['body'], img, 
                                              start, end, spacing)

    # draw comment footer to last frame
    last_img = Image.fromarray(frames[-1])
    draw_comment_footer_to_image(img, text_end)
    frames[-1] = np.array(last_img)

    return frames, img, text_end



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



# used in create_comment_video below
get_file_name_for_comment = lambda n: comment_video_name_base + str(n) + '.mp4'

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
    out    = cv2.VideoWriter(os.path.join(temp_dir, video_name), fourcc, fps, (width, height))

    comment['body'] = strip_newlines(comment['body'])

    durations        = create_comment_audio(comment['body'])
    frames, img, end = create_comment_frames(comment, img, start)

    cv2_frames = [cv2.cvtColor(frame, cv2.COLOR_RGBA2BGR) for frame in frames]

    for frame, duration in list(zip(cv2_frames, durations)):
        for _ in range(int(fps * duration * magic_audio_constant)):
            out.write(frame)

    out.release()
    cv2.destroyAllWindows()

    comment_video_name = get_file_name_for_comment(comment_n)
    subprocess.run(f"ffmpeg -i {temp_dir}/{video_name} -i {temp_dir}/{audio_name} -c copy -map 0:v:0 -map 1:a:0 {working_dir}/{comment_video_name}", shell=True, timeout=120)

    return img, end, comment_video_name




# creates several subvideos and makes a call to ffmpeg to concatenate them
def create_comment_chain_video(comment):
    img = Image.new("RGBA", (width, height), background_color)
    comment_n = 0
    file_names = []

    # TODO this is temporary. Must preprocess comment chain and compute total comment height
    # for each comment beforehand, and loop through the "comment structure" 
    # given by `comment` argument to the function, keeping track of 
    pos = (text_start_x, text_start_y)
    img, end, file_name = create_comment_video(comment, img, pos, comment_n)
    comment_n += 1
    file_names.append(working_dir + '/' + file_name)

    # TODO temporary read above
    pos = end[0] + 50, end[1] + 80
    img, end, file_name = create_comment_video(comment['replies'][0], img, pos, comment_n)
    comment_n += 1
    file_names.append(working_dir + '/' + file_name)

    file_names_txt_file = working_dir + '/comment_videos.txt'

    with open(file_names_txt_file, 'w') as f:
        for file_name in file_names:
            f.write('file \'' + file_name + '\'\n')

    subprocess.run(f"ffmpeg -f concat -safe 0 -i {file_names_txt_file} -c copy {base_dir}/{final_video_name}", shell=True, timeout=120)

    return False


if __name__ == '__main__':
    #load_top_posts_and_best_comments('AmItheAsshole')
    with codecs.open('posts.json', 'r', 'utf-8') as posts_file:
        posts = json.load(posts_file)
    create_comment_chain_video(posts[0]["comments"][0])



