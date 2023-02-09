# load_posts.py

import requests
import json
import codecs
import praw
from praw.models import Redditor, Comment, MoreComments

class NotEnoughCommentsError(Exception):
    pass

score_limit = 1000
char_limit  = 1000
max_n_replies = 3

awards_dir = 'res/awards/'
awards_retrieved_fname = awards_dir + 'retrieved.txt'
awards_retrieved = []

def save_awards_retrieved():
    with open(awards_retrieved_fname, 'w') as retrieved_f:
        for award_id in awards_retrieved:
            retrieved_f.write(award_id + '\n')

def load_awards_retrieved():
    with open(awards_retrieved_fname, 'r') as retrieved_f:
        awards_retrieved = [line.strip() for line in retrieved_f.readlines()]

def retrieve_award_icon(award_id, url):
    response = requests.get(url)
    with open(awards_dir + award_id + '.png', 'wb') as award_icon_f:
        award_icon_f.write(response.content)

def get_awards(comment):
    awards = []
    for award in comment.all_awardings:
        if award['id'] not in awards_retrieved:
            # this line assumes reddit api will always populates this key
            # with dictionaries and only provides one dict with width key equal to 48
            url = [url_dict['url'] for url_dict in award['resized_static_icons'] 
                        if url_dict['width'] == 128][0]
            retrieve_award_icon(award['id'], url)
        awards.append({
            'id': award['id'],
            'count': award['count'],
        })
    return awards

def prune_posts(posts):
    top_posts = []
    for post in posts:
        post.comments.replace_more(limit=0)
        top_posts.append({
            'title': post.title,
            'score': post.score,
            'url': post.url,
            'permalink': post.permalink,
            'author': post.author.name,
            'content': post.selftext,

            # will call similar function on each reply in forest
            'comments': prune_comments(post.comments)
        })
    return top_posts

def prune_comments(comments):
    top_comments = []
    print(comments)
    for comment in comments:
        if isinstance(comment, MoreComments):
            continue;
        if comment.score > score_limit and len(comment.body) <= char_limit:
            # deleted comment
            if comment.author is None:
                continue;
            top_comments.append({
                'author': comment.author.name,
                'score':  comment.score,
                'permalink': comment.permalink,
                'body':   comment.body,
                'created_utc': comment.created_utc,
                'id': comment.id,
                'is_submitter': comment.is_submitter,
                'edited': comment.edited,
                'awards': get_awards(comment),

                # called function here must be different from prune_comments
                # as prune_replies will be called recursively
                'replies': prune_replies(comment.replies)
            })
        if len(top_comments) > max_n_replies:
            break;
    return top_comments

def prune_replies(replies):
    top_replies = []
    for reply in replies:
        if isinstance(reply, MoreComments):
            continue;
        if reply.score > score_limit and len(reply.body) <= char_limit:
            if reply.author is None:
                continue;
            top_replies.append({
                'author': reply.author.name,
                'score':  reply.score,
                'permalink': reply.permalink,
                'body':   reply.body,
                'created_utc': reply.created_utc,
                'id': reply.id,
                'is_submitter': reply.is_submitter,
                'edited': reply.edited,
                'awards': get_awards(reply),

                # call this function recursively
                'replies': prune_replies(reply.replies)
            })
        if len(top_replies) > max_n_replies:
            break;
    return top_replies

def save_top_posts_and_best_comments(subreddit_name):
    load_awards_retrieved()
    reddit = praw.Reddit(client_id=    'Sx5GE4fYzUuNLwEg_h8k4w',
                         client_secret='0n4qkZVolBDeR2v5qq6-BnSuJyhQ7w',
                         user_agent=   'python-script')
    subreddit = reddit.subreddit(subreddit_name)
    #posts = subreddit.top(limit=10, time_filter='all')
    posts = subreddit.top(limit=1, time_filter='all')
    posts_data = prune_posts(posts)
    with codecs.open('posts.json', 'w', 'utf-8') as json_file:
        json.dump(posts_data, json_file)
    save_awards_retrieved()

if __name__ == '__main__':
    save_top_posts_and_best_comments('AmItheAsshole')

