from gcodeparser import parse_gcode_lines
import PySimpleGUI as psg
from psg_util import get_float_or_exit
import os
#import sys

print('Shift the G Code origin from bottom left to the center of the workpiece\n')

nc_input_file = psg.popup_get_file('Enter file to be shifted', file_types = (('GCode', '*.nc'),))
split_file = os.path.splitext(nc_input_file)
nc_output_default = split_file[0] + '_shifted' + split_file[1]
nc_output_file = psg.popup_get_file('Enter file to be output', save_as = True, default_extension = '.nc', default_path = nc_output_default, file_types = (('GCode', '.nc'),))

x_offset = get_float_or_exit('Enter the X offset of the workpiece center from the origin')
y_offset = get_float_or_exit('Enter the Y offset of the workpiece center from the origin')

nc_input = open(nc_input_file, 'r')
nc_output = open(nc_output_file, 'w')

print(f'; ShiftOrigin processed {nc_input_file} X offset: {x_offset} Y offset: {y_offset}\n;\n', file = nc_output)

for line in parse_gcode_lines(nc_input, include_comments = True):
    x = line.get_param('X')
    if x and (type(x) == float or type(x) == int):
        line.update_param('X', x - x_offset)
    y = line.get_param('Y')
    if y and (type(y) == float or type(y) == int):
        line.update_param('Y', y - y_offset)
    print(line.gcode_str, file = nc_output)

nc_input.close()
nc_output.close()