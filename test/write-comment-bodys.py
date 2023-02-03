import codecs
import json
import re

#with codecs.open('../posts.json', 'r', 'utf-8') as posts_file:
#    posts = json.load(posts_file)
#    with codecs.open('body1.txt', 'w', 'utf-8') as f_body:
#        f_body.write(posts[0]["comments"][0]["body"])
#    with codecs.open('body2.txt', 'w', 'utf-8') as f_body:
#        f_body.write(posts[0]["comments"][0]["replies"][0]["body"])

def insert_spaces_after_sentences(paragraph):
    result = ''
    for i in range(len(paragraph)):
        char = paragraph[i]
        result += char
        if char == '.' and (i + 1 >= len(paragraph) or paragraph[i + 1] != ' '):
            result += ' '
    return result

def get_sentences(content):
    return [s.strip() + '.' for s in re.split("[!?.]", content) if len(s) > 1]

def cleanup_paragraphs(paragraphs):
    # go through the list and join together all adjacent paragraphs 
    # that have two sentences or less.
    result = []
    joined_paragraph = ''
    for paragraph in paragraphs:
        sentences = get_sentences(paragraph)
        if len(sentences) < 2:
            joined_paragraph += paragraph
        else:
            result.append(joined_paragraph)
            result.append(paragraph)
    return [insert_spaces_after_sentences(p) for p in result if p != '']

def get_paragraphs(content):
    paras = [s for s in content.split("\\n") if s]
    return paras

def clean(text):
    return False


body = ''

with open('body1.txt') as f_body:
    c = 'z'
    while c:
        c = f_body.read(1)
        if c == '\n':
            body += '\\n'
            continue
        body += c

print(body + '\n\n')
paragraphs = get_paragraphs(body)
print(paragraphs)
print('\n\n')
print(len(paragraphs))
for para in paragraphs:
    print(para)

body_clean = clean(body)


def strip_newlines(text):
    return text.replace('\n', '')

def strip_excess_newlines(text):
    pattern = r'(\n)+'
    return re.sub(pattern, '\n', text)

