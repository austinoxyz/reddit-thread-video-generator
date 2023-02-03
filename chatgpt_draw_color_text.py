from PIL import Image, ImageDraw, ImageFont
import freetype

# initialize the FreeType library
face = freetype.Face("Roboto-Regular.ttf")
face.set_char_size(48 * 64)

# create a new image and get a drawing context
image = Image.new("RGBA", (800, 800), (255, 255, 255, 255))
draw = ImageDraw.Draw(image)

# set the text color to red
text_color = (255, 0, 0, 255)

# render the text on the image
text = "Hello, World!"
face.load_char("H")
bitmap = face.glyph.bitmap
x = 0
y = 0
for i in range(len(text)):
    face.load_char(text[i])
    bitmap = face.glyph.bitmap
    draw.text((x + face.glyph.bitmap_left, y - face.glyph.bitmap_top + face.glyph.bitmap.rows),
              text[i], font=ImageFont.truetype("Roboto-Regular.ttf", 48), fill=text_color)
    x += face.glyph.advance.x >> 6
    y += face.glyph.advance.y >> 6

# save the image to a file
image.save("text.png")
