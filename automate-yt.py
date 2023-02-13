# automate-youtube.py

import math
import os
import re
import time
import datetime
import json
import codecs

import numpy as np
import freetype
from PIL import Image, ImageDraw
from gtts import gTTS
from pydub import AudioSegment
import cv2
import subprocess

from load_posts import save_top_posts_and_best_comments
from text_clean import clean_comment_bodies, get_paragraphs, get_sentences, replace_acronyms

from util import *
from text_render import *




# Fonts 
title_font = new_font('./fonts/Roboto-Regular.ttf', 64)
sub_font = new_font('./fonts/Roboto-Bold.ttf', 32)
title_header_font = new_font('./fonts/Roboto-Regular.ttf', 28)
comment_font = new_font('./fonts/Roboto-Regular.ttf', 32)
header_font = new_font('./fonts/Roboto-Regular.ttf', 24)
op_font = new_font('./fonts/Roboto-Bold.ttf', 20)

add_font_to_registry('./fonts/Roboto-Regular.ttf', 64, 'title')
add_font_to_registry('./fonts/Roboto-Bold.ttf', 32, 'sub')
add_font_to_registry('./fonts/Roboto-Regular.ttf', 28, 'title_header')
add_font_to_registry('./fonts/Roboto-Regular.ttf', 32, 'comment')
add_font_to_registry('./fonts/Roboto-Regular.ttf', 24, 'header')
add_font_to_registry('./fonts/Roboto-Bold.ttf', 20, 'op')


# Images
upvote_img = Image.open('./res/upvote.png').convert("RGBA")
upvote_dim = (38, 38)
upvote_img = upvote_img.resize(upvote_dim)

downvote_img  = Image.open('./res/downvote.png').convert("RGBA")
downvote_dim = (38, 38)
downvote_img  = downvote_img.resize(downvote_dim)

footer_img  = Image.open('./res/comment_footer.png').convert("RGBA")
footer_img_dim = (578, 48)
footer_img = footer_img.resize(footer_img_dim)


fps = 30

indent_off  = 50
header_off  = 50
sidebar_off = 50, 50

vote_img_pad = 100
comment_end_pad = footer_img.height + 100

total_chain_height = 0
img_height = 0



# Project Structure
working_dir = 'build-vid/'
temp_dir    = working_dir + 'tmp/'

title_audio_name     = 'title.mp3'
na_title_video_name  = 'na_title_card.mp4'
title_card_file_name = 'title_card.mp4'

file_names_txt_file = working_dir + 'comment_videos.txt'

na_video_name  = 'audioless_video.mp4'
audio_name  = 'audio.mp3'
static_video_name = 'static.mp4'
final_video_name = 'final.mp4'
comment_video_name_base = 'comment'
chain_video_name_base   = 'chain'

comment_n = 0
chain_n = 0





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
        first = npoints // 100000
        second = ((npoints // 1000) % 1000) // 10
        multiplier = 'm'
    elif npoints >= 1000:
        first = npoints // 1000
        second = (npoints % 1000) // 10
        multiplier = 'k'
    return str(first) + '.' + str(second) + multiplier + ' points'

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

def sec_2_vid_duration(sec):
    minutes = sec / 60
    return str(int(math.floor(int(sec) / 60))) + ':' + '{:0>2}'.format(str(int(sec) % 60))


def compute_comment_height(comment, width_box):
    body_h = get_bounded_text_height(comment['body'], comment_font, width_box)
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
    body_height = get_bounded_text_height(comment['body'], comment_font, width_box)
    height = body_height - downvote_img.height + comment_end_pad - header_off - 25
    if comment.get('replies') is None:
        return height
    for reply in comment['replies']:
        height += total_comment_height(reply, (start_x + indent_off, end_x))
    return height

def draw_awards(img, pos, awards):
    (x, y) = pos
    for i, award in enumerate(awards):
        award_img = Image.open('./res/awards/' + award['id'] + '.png').convert("RGBA")
        award_dim = (48, 48)
        award_img = award_img.resize(award_dim)
        img.paste(award_img, (x, y - int(award_dim[1] / 3)), award_img)
        x += award_dim[0]
        if award['count'] > 1:
            x += 5
            (x, y) = draw_string_to_image(str(award['count']), img, (x, y), header_font, GRAY)
        x += 10
        if x > text_width_cutoff - 80:
            x += 10
            n_remaining = len(awards) - i - 1
            (x, y) = draw_string_to_image(f"+ {n_remaining} more", img, (x, y), header_font, WHITE)
            break;
    return (x, y)

def draw_header(img, pos, username, npoints, created_utc, is_submitter, awards):
    (x, y) = pos[0], pos[1] - header_off
    draw  = ImageDraw.Draw(img)
    draw_debug_line_y(img, y, PINK)

    # write the username above the image
    username_color = (22, 210, 252, 1)
    (x, y) = draw_string_to_image('u/' + username, img, (x, y), header_font, username_color)
    x += 10

    if is_submitter:
        (x, y) = draw_string_to_image('OP', img, (x, y), op_font, RED)
        x += 10

    # write the points and time duration after the username 
    string = ' •   ' + points_str(npoints) + '   •   ' + time_ago_str(created_utc)
    (x, y) = draw_string_to_image(string, img, (x, y), header_font, WHITE)
    x += 10

    # paste the medals
    draw_awards(img, (x, y), awards)

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



def write_comment(comment, img, pos):
    x, y = pos
    width_box = (x, text_width_cutoff)
    spacing = int((comment_font.height >> 6) * 1.2)
    color = (255, 255, 255, 1)
    frames = []

    draw_debug_line_x(img, width_box[0], BLUE)
    draw_debug_line_x(img, width_box[1], BLUE)

    draw_debug_line_y(img, y, YELLOW)
    body_height_dbg = get_bounded_text_height(comment['body'], comment_font, width_box)
    draw_debug_line_y(img, y + body_height_dbg, YELLOW)
    total_height_dbg = total_comment_height(comment, width_box)
    if comment_n == 0:
        draw_debug_line_y(img, y + total_height_dbg, CYAN)
    else:
        draw_debug_line_y(img, y + total_height_dbg, RED)


    LOG('START WRITE COMMENT', comment['body'])
    for paragraph in get_paragraphs(comment['body']):
        paragraph_frames, (x, y) = write_paragraph(paragraph, img, (x, y), width_box, comment_font, spacing, color)
        frames = frames + paragraph_frames
    LOG('END WRITE COMMENT', '', (x, y))
    return frames, (x, y)




def create_comment_frames(comment, img, start):
    x, y = start

    # draw sidebar
    line_height = compute_line_height(comment, (x, text_width_cutoff))
    draw_sidebar(img, (x, y), line_height)

    # draw header
    draw_header(img, (x, y), comment['author'], comment['score'], comment['created_utc'], comment['is_submitter'], comment['awards'])

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

    LOG('WRITING VIDEO', sec_2_vid_duration(sum(durations)))
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
    subprocess.run(f"ffmpeg -i {temp_dir}{na_video_name} -i {temp_dir}{audio_name} \
                    -c copy -map 0:v:0 -map 1:a:0 -y ./{working_dir}{out_file_name} > /dev/null 2>&1", 
                   shell=True, timeout=300)
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

# creates several subvideos and concatenates them with ffmpeg
def create_comment_chain_video(comment):
    #if (more_replies_than_desired(comment)):
    #    raise MoreRepliesThanDesiredError("too many replies doofus.")

    # scroll pane
    global pane_y, total_chain_height, img_height
    pane_y = 0
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
    img = Image.new("RGBA", (screen_width, img_height), BACKGROUND)

    end, file_names = create_comment_video(comment, img, (x, y))

    with open(file_names_txt_file, 'w') as f:
        for file_name in file_names:
            f.write('file \'' + file_name + '\'\n')

    global chain_n
    out_file_name = chain_video_name_base + str(chain_n) + '.mp4'
    subprocess.run(f"ffmpeg -f concat -safe 0 -i {file_names_txt_file} -c copy \
                    -y ./{working_dir}{out_file_name} > /dev/null 2>&1", 
                   shell=True, timeout=120)
    LOG('VIDEO CREATED', out_file_name)
    chain_n += 1

    return out_file_name

def draw_title_header(img, pos, subreddit, username, created_utc, awards):
    (x, y) = pos[0] + 50, pos[1] - header_off

    (x, y) = draw_string_to_image('r/' + subreddit, img, (x, y), sub_font, WHITE)
    x += 10

    string = ' •   Posted by u/' + username + '   •   ' + time_ago_str(created_utc)
    (x, y) = draw_string_to_image(string, img, (x, y), title_header_font, GRAY)
    x += 10

    draw_awards(img, (x, y), awards)
    return False

def draw_title_sidebar(img, pos, score):
    return False

def draw_title_footer(img, pos, num_comments):
    return False

def create_title_frame(post):
    img = Image.new("RGBA", (screen_width, screen_height), BACKGROUND)
    (x, y) = (text_start_x, int(screen_height / 3))
    width_box = (x, text_width_cutoff)
    spacing = int((title_font.height >> 6) * 1.8)
    draw_title_header(img, (x, y), post['subreddit'], post['author'], 
                      post['created_utc'], post['awards'])
    draw_title_sidebar(img, (x, y), post['score'])
    (x, y) = write_sentence(post['title'], img, (x, y), width_box, title_font, spacing, WHITE)
    draw_title_footer(img, (x, y), post['num_comments'])
    return np.array(img)


def create_title_video(post):
    title_audio_name     = 'title.mp3'
    na_title_video_name  = 'na_title_card.mp4'
    out_file_name = 'title_card.mp4'

    frame = create_title_frame(post)
    duration = create_audio_file(post['title'], title_audio_name)

    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    out    = cv2.VideoWriter(os.path.join(temp_dir, na_title_video_name), fourcc, fps, (screen_width, screen_height))
    frame  = cv2.cvtColor(frame, cv2.COLOR_RGBA2BGR)
    for _ in range(int(fps * duration)):
        out.write(frame)
    out.release()
    cv2.destroyAllWindows()

    subprocess.run(f"ffmpeg -i {temp_dir}{na_title_video_name} -i {temp_dir}{title_audio_name} \
            -c copy -map 0:v:0 -map 1:a:0 -y ./{working_dir}{out_file_name} > /dev/null 2>&1", 
            shell=True, timeout=300)
    return out_file_name


# TODO partially implemented not working
def create_final_video(post):

    # create title card
    title_card_file_name = create_title_video(post)

    # create separate video for each top level comment and its replies
    global chain_n
    chain_n = 0
    file_names = []
    for comment in post['comments']:
        chain_file_name = create_comment_chain_video(comment)
        file_names.append(chain_file_name)

    # join together chain videos with 'static video' in between, with title-card first
    with open(file_names_txt_file, 'w') as f:
        f.write('file \'' + title_card_file_name + '\'\n')
        for file_name in file_names[:-1]:
            f.write('file \'' + file_name + '\'\n')
            f.write('file \'../res/' + static_video_name + '\'\n')
        f.write('file \'' + file_names[-1] + '\'\n')


    LOG('CREATING FINAL VIDEO...', '')
    subprocess.run(f"ffmpeg -f concat -safe 0 -i {file_names_txt_file} -c copy \
                    -crf 20 -preset veryfast \
                    -y {final_video_name}", 
                   shell=True, timeout=120)
    #subprocess.run(f"ffmpeg -f concat -safe 0 -i {file_names_txt_file} \
    #               -c:v libx264 -crf 20 -preset veryfast \
    #               -y {final_video_name}", 
    #               shell=True, timeout=120)
    LOG('FINAL VIDEO CREATED', '')

if __name__ == '__main__':
    score_limit = 1000
    max_n_replies = 4
    with codecs.open('data/posts.json', 'r', 'utf-8') as posts_file:
        posts = json.load(posts_file)
    for comment in posts[0]['comments']:
        clean_comment_bodies(comment)

    #create_title_video(posts[0])
    
    # uncomment to test create_comment_chain_video with
    # a long video that should take roughly 3:14 seconds to generate
    #
    #posts[0]['comments'][0]['replies'] += posts[0]['comments'][1]['replies']
    #create_comment_chain_video(posts[0]['comments'][0])

    # uncomment to test create_final_video 
    # with a short video with two comment chains
    #
    posts[0]['comments'] = posts[0]['comments'][:2]
    posts[0]['comments'][1]['replies'] = posts[0]['comments'][1]['replies'][:3] 
    for comment in posts[0]['comments']:
        for reply in comment['replies']:
            reply['replies'] = []
    create_final_video(posts[0])


