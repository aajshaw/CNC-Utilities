from PIL import Image
import PySimpleGUI as psg
from os import path
from math import sqrt, pi, sin
from operator import itemgetter
from typing import NamedTuple
from sys import exit

FULL = 255

class Distance(NamedTuple):
    x: int
    y: int
    distance: float

class Pixel(NamedTuple):
    red: int
    green: int
    blue: int
    alpha: int

def get_int(text: str, default: str = '') -> int:
    while True:
        value = psg.popup_get_text(text, default_text = default)
        if value is None:
            exit()
        try:
            value = int(value)
            break
        except ValueError:
            psg.popup_timed('Enter an integer number', auto_close_duration = 5    )
    return value

def make_distance_list(limit: int) -> list[Distance]:
    distances = []
    for x in range(-limit, limit + 1):
        for y in range(-limit, limit + 1):
            if sqrt(x**2 + y**2) <= limit and (x != 0 or y != 0):
                distances.append(Distance(x, y, sqrt(x**2 + y**2)))

    # Order the list of distances so that they can be checked
    # cloest first
    distances.sort(key = itemgetter(2))

    return distances

def nearest_not_green(bitmap: list[list[Pixel]], distances: list[Distance], x: int, y: int, limit: int) -> float:
    y_len = len(bitmap)
    x_len = len(bitmap[0])
    for dxy in distances:
        offset_x = x + dxy.x
        offset_y = y + dxy.y
        if offset_x >= 0 and offset_x < x_len and offset_y >= 0 and offset_y < y_len:
            if not bitmap[offset_y][offset_x].green:
                return dxy.distance

    return limit

def nearest_not_blue(bitmap: list[list[Pixel]], distances: list[Distance], x: int, y: int, limit: int) -> float:
    y_len = len(bitmap)
    x_len = len(bitmap[0])
    for dxy in distances:
        offset_x = x + dxy.x
        offset_y = y + dxy.y
        if offset_x >= 0 and offset_x < x_len and offset_y >= 0 and offset_y < y_len:
            if not bitmap[offset_y][offset_x].blue:
                return dxy.distance

    return limit

green_range: int = get_int('Enter range for searching from a green pixel', default = '100')

from_green_distances = make_distance_list(green_range)

blue_range: int = get_int('Enter range for searching from a blue pixel', default = '100')

from_blue_distances = make_distance_list(blue_range)

png_imput_file = psg.popup_get_file('Select file be contoured', file_types = (('PNG Files', '*.png'),))

image = Image.open(png_imput_file)
image.load()

print('Importing image...', end = '', flush = True)
bitmap: list[list[Pixel]] = []
for y in range(image.height):
    row: list[Pixel] = []
    for x in range(image.width):
        pixel = Pixel(*image.getpixel((x, y))) # type: ignore
        row.append(pixel)
    bitmap.append(row)
print('Done')

# process the bitmap looking for green pixels and finding the distance
# to the nearest red pixel
print('Processing bitmap', end = '', flush = True)
percent = -1
for y in  range(len(bitmap)):
    cur_percent = int(y / len(bitmap) * 100)
    if cur_percent > percent:
        percent = cur_percent
        print(f'.({percent}%)', end = '', flush = True)
    row = bitmap[y]
    for x in range(len(row)):
        pixel = bitmap[y][x]
        if pixel.green:
            distance = nearest_not_green(bitmap, from_green_distances, x, y, green_range)
            # pi / 180 = 1 degree
            # 90 * (distance / RANGE) = degree from 1 to 90
            # sin of the above gives between ~0.0 to ~1.0
            # use the value to give a GREEN between 0 and 255
            new_green = int((FULL * sin((pi / 180) * (90 * (distance / green_range)))) + 0.5)
            bitmap[y][x] = Pixel(0, new_green, 0, FULL)
        elif pixel.blue:
            distance = nearest_not_blue(bitmap, from_blue_distances, x, y, blue_range)
            # pi / 180 = 1 degree
            # 90 * (distance / RANGE) = degree from 1 to 90
            # sin of the above gives between ~0.0 to ~1.0
            # use the value to give a BLUE between 0 and 255
            new_blue = int((FULL * sin((pi / 180) * (90 * (distance / blue_range)))) + 0.5)
            bitmap[y][x] = Pixel(0, 0, new_blue, FULL)

print('.Done')

output_image = Image.new('RGBA', (image.width, image.height))
for y in range(len(bitmap)):
    row = bitmap[y]
    for x in range(len(row)):
        output_image.putpixel((x, y), (row[x].red, row[x].green, row[x].blue, row[x].alpha))
png_output_file = psg.popup_get_file('Output file', save_as= True, default_extension = '.png', file_types = (('PNG', '.png'),))
output_image.save(png_output_file)