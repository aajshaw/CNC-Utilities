from PIL import Image
import PySimpleGUI as psg
from os import path

RED = 0
GREEN = 1
BLUE = 2
ALPHA = 3

png_imput_file = psg.popup_get_file('Select file be contoured', file_types = (('PNG Files', '*.png'),))

image = Image.open(png_imput_file)
image.load()

print('Processing image', end = '', flush = True)
percent = -1
for x in range(image.width):
#    print(f'Processing column {x}')
    cur_percent = int(x / image.width * 100)
    if cur_percent > percent:
        percent = cur_percent
        print(f'.({percent}%)', end = '', flush = True)
    for y in range(image.height):
        pixel: float | tuple[int, ...] | None = image.getpixel((x, y))
        if pixel[ALPHA] == 0:
            image.putpixel((x, y), (255, 0, 0, 255)) # Full red
        else:
            image.putpixel((x, y), (0, 255, 0, pixel[ALPHA]))
print('.Done')

def_output_file = path.splitext(png_imput_file)[0] + '_color.png'
png_output_file = psg.popup_get_file('Output file', save_as= True, default_extension = '.png', file_types = (('PNG', '.png'),))

image.save(png_output_file)