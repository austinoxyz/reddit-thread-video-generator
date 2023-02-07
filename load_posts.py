# load_posts.py

import json
import codecs
import praw
from praw.models import Redditor, Comment, MoreComments

class NotEnoughCommentsError(Exception):
    pass

def get_awards(comment):
    awards = []
    for award in comment.all_awardings:
        print(award['name'])
        awards.append({
            'name': award['name'],
            'count': award['count']
        })
    return awards

def prune_posts(posts, score_limit, max_n_replies):
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
            'comments': prune_comments(post.comments, score_limit, max_n_replies) 
        })
    return top_posts

def prune_comments(comments, score_limit, max_n_replies):
    top_comments = []
    print(comments)
    for comment in comments:
        if isinstance(comment, MoreComments):
            continue;
#        if i == 0:
#            for attribute in dir(comment):
#                print(attribute)
        if comment.score > score_limit:
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
                'replies': prune_replies(comment.replies, score_limit, max_n_replies)
            })
        if len(top_comments) > max_n_replies:
            break;
    return top_comments

def prune_replies(replies, score_limit, max_n_replies):
    top_replies = []
    for reply in replies:
        if isinstance(reply, MoreComments):
            continue;
        if reply.score > score_limit:
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
                'replies': prune_replies(reply.replies, score_limit, max_n_replies)
            })
        if len(top_replies) > max_n_replies:
            break;
    return top_replies

def save_top_posts_and_best_comments(subreddit_name):
    reddit = praw.Reddit(client_id=    'Sx5GE4fYzUuNLwEg_h8k4w',
                         client_secret='0n4qkZVolBDeR2v5qq6-BnSuJyhQ7w',
                         user_agent=   'python-script')
    subreddit = reddit.subreddit(subreddit_name)
    posts = subreddit.top(limit=10, time_filter='all')
    posts_data = prune_posts(posts, 1000, 5)
    with codecs.open('posts.json', 'w', 'utf-8') as json_file:
        json.dump(posts_data, json_file)

if __name__ == '__main__':
    save_top_posts_and_best_comments('AmItheAsshole')

