from gcodeparser import parse_gcode_lines
import PySimpleGUI as psg
import os
import sys

def get_float(text: str, default: str = '') -> float:
    while True:
        value = psg.popup_get_text(text, default_text = default)
        if value is None:
            sys.exit()
        try:
            value = float(value)
            break
        except ValueError:
            psg.popup_timed('Enter a floating point number', auto_close_duration = 5    )
    return value

print('Shift the G Code origin from bottom left to the center of the workpiece\n')

#nc_input_file = input('Enter file to be shifted: ')
nc_input_file = psg.popup_get_file('Enter file to be shifted', file_types = (('GCode', '*.nc'),))
#nc_output_file = input('Enter file to be output: ')
split_file = os.path.splitext(nc_input_file)
nc_output_default = split_file[0] + '_shifted' + split_file[1]
nc_output_file = psg.popup_get_file('Enter file to be output', save_as = True, default_extension = '.nc', default_path = nc_output_default, file_types = (('GCode', '.nc'),))

x_offset = get_float('Enter the X offset of the workpiece center from the origin')
y_offset = get_float('Enter the Y offset of the workpiece center from the origin')

nc_input = open(nc_input_file, 'r')
nc_output = open(nc_output_file, 'w')

print(f'; ShiftOrigin processed {nc_input_file} X offset: {x_offset} Y offset: {y_offset}\n;\n', file = nc_output)

for line in parse_gcode_lines(nc_input, include_comments = True):
    x = line.get_param('X')
    if x:
        line.update_param('X', x - x_offset)
    y = line.get_param('Y')
    if y:
        line.update_param('Y', y - y_offset)
    print(line.gcode_str, file = nc_output)

nc_input.close()
nc_output.close()