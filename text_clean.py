test_text = "NTA\n\n\
This is a recurring theme here on Reddit, people do not consider themselves thieves:\n\n\
> Sammy and his daughters saw the lock and weren't happy, the girls were extremely upset. Sammy asked about it and I straight up told him. He said \"my daughters aren't thieves!!!\n\n\
They seem to be under the wrongful impression that to be a thief you *have to* wear a mask and carry a crowbar. But theft is:\n\n\
**Theft** is the taking of another person's property or services without that person's permission or consent with the intent to deprive the rightful owner of it. -- [Theft - Wikipedia](https://en.wikipedia.org/wiki/Theft)\n\n\
This is literally what they have been doing. Taking stuff that wasn't theirs. And the rightful owner incurred a loss.\n\n\
Sammy, who is your *guest*, sounds like an AH:\n\n\
> he said Zoey could easily get another makeup kit for 15 bucks from walmart \n\n\
While this is probably true, it is none of his business. And doesn't change a thing. If you steal from a store then the store owner could just get more stuff, but nobody (should) considers that to be an excuse.\n\n\
> [he said Zoey] shouldn't even be buying expensive - adult makeup in the first place and suggested my wife take care of this \"defect\" in Zoey's personality trying to appear older than she is. \n\n\
Instead of talking to his kids, he *blames the victim*. \"We took her stuff, because *she* shouldn't have said stuff. It would be better *my kids* had *her* stuff! Ugh!\n\n\
> He accused me of being overprotective and babying Zoey with this level of enablement. \n\n\
Not only does Sammy refuse to teach *his* kids not to take other people's things, he also considers *you* to be a bad parent. Even *if* you were incorrect in how you raise your kid, even *if* it would be better if your daughter shared her make-up, he is in *no position* to demand it, and his daughters, who are *guests in your house*, should follow reasonable \"house rules\".\n\n\
Your wife is choosing her brother over her daughter (and you), and hasn't thought things through. What if they next go through *her* things? What if Sammy next goes through her underwear?!? Where does it end? Expecting people not to go through other people's stuff in perfectly reasonable. Sammy is an entitled ass.\n\n"

#..of it. -- [Theft - Wikipedia](https://en.wikipedia.org/wiki/Theft)

import re

def remove_markdown_links(text):
    return re.sub(r"\(https://.*\)", '', text)

def get_paragraphs(text):
    return [s for s in re.split('(\n)+', text) if re.search(r"\S", s)]

sent_delims = ['.', '!', '?', ':', ';', ',', '-']

def get_sentences(paras):
    sentences = []
    sent, word = '', ''
    for para in paras:
        for i, c in enumerate(para):
            if c == ' ':
                sent += word + ' '
                word = ''
                continue;
            elif c in sent_delims:
                # hyphens are tricky
                if c == '-' and i != len(para) - 1 and para[i+1] != ' ':
                    word += c
                    continue;
                sent += word
                sentences.append(sent + c)
                word = ''
                sent = ''
            else:
                word += c
    sentences = [s.strip() for s in sentences if s]

    modifications = []
    curr_idx = 0
    for i, s in enumerate(sentences):
        if len(s) == 1 and s in sent_delims:
            modifications.append((i, curr_idx))
        else:
            curr_idx = i
    for modif in modifications:
        sentences[modif[1]] += sentences[modif[0]]
    return [s for s in sentences if len(s) > 1]

def add_punctuation_to_paragraphs(text):
    text = text.strip()
    paras = get_paragraphs(text)
    for i, para in enumerate(paras):
        if para[-1] not in ['.','!','?',':','-']:
            paras[i] += '.'
    return '\n'.join(paras)

def clean_comment_body(body):
    body = remove_markdown_links(body)
    body = add_punctuation_to_paragraphs(body)
    return body

if __name__ == '__main__':
    test_text = clean_comment_body(test_text)
    paras = get_paragraphs(test_text)
    sentences = get_sentences(paras)

