# util.py

from PIL import Image, ImageDraw

# Colors
RED    = (255,   0,   0, 1)
GREEN  = (  0, 255,   0, 1)
BLUE   = (  0,   0, 255, 1)
CYAN   = (  0, 255, 255, 1)
PINK   = (252,  17, 154, 1)
YELLOW = (252, 248,  22, 1)
ORANGE = (252, 127,  17, 1)
MAROON = ( 68,   2,   2, 1)
GRAY   = (153, 153, 153, 1)
WHITE  = (255, 255, 255, 1)
BLACK  = (  0,   0,   0, 1)

BACKGROUND = (26, 26, 27, 0)



def flatten(lst):
    flattened_list = []
    for item in lst:
        if isinstance(item, list):
            flattened_list.extend(flatten(item))
        else:
            flattened_list.append(item)
    return flattened_list


debug = False
#debug = True

def LOG(title, message, pos=''):
    if len(title) > 32:
        title = title[:32]
    title = '[' + title + ']'
    if len(message) > 48:
        message = message[:48] + '...'
    print('{:<32}'.format(title), end='')
    print(' | {:<16}'.format(str(pos)), end='')
    if message:
        print(f' | {message}')
        return
    print(' | \n', end='')


def draw_debug_line_y(img, y, color):
    if not debug:
        return
    draw = ImageDraw.Draw(img)
    dbg_ln_start, dbg_ln_end = (0, y), (screen_width, y)
    draw.line([dbg_ln_start, dbg_ln_end], fill=color, width=2)

def draw_debug_line_x(img, x, color):
    if not debug:
        return
    draw = ImageDraw.Draw(img)
    dbg_ln_start, dbg_ln_end = (x, 0), (x, screen_height)
    draw.line([dbg_ln_start, dbg_ln_end], fill=color, width=2)


