import PySimpleGUI as psg
from psg_util import get_float_or_exit, get_int_or_exit
from math import ceil

def nc_header(nc_file):
    print('; Header', file = nc_file)
    print('G21', file = nc_file)
    print('M3 S10000', file = nc_file)
    print('G90', file = nc_file)
    #print('G1 Z3 F228.6', file = nc_file)
    nc_move_to_safe(nc_file)

def nc_trailer(nc_file):
    print('; Trailer', file = nc_file)
    #print('G1 Z3 F228.6', file = nc_file)
    nc_move_to_safe(nc_file)
    print('G0 X0 Y0', file = nc_file)
    print('G4 P0.1', file = nc_file)
    print('M5', file = nc_file)

def nc_move_to_safe(nc_file):
    print('G1 Z3 F228.6', file = nc_file)

def nc_raster_cut(nc_file, size_x, size_y, size_z, bit_size, horizontal_overcut_percent = 33, feed_rate = 750.0, plunge_rate = 225.0, depth_per_pass = 0.5, start_x = 0, start_y = 0, start_z = 0, tool_centered = True):
    print('; Raster cut a level', file = nc_file)

    bit_radius = bit_size / 2

    if tool_centered:
        # move to bottom left corner
        x = start_x - (size_x / 2) + (bit_radius)
        y = start_y - (size_y / 2) + (bit_radius)
    else:
        x = start_x + (bit_radius)
        y = start_y + (bit_radius)

    # Calculate the y offset for each pass to account for the horizaontal overcut percentage
    overcut_fraction = 1 - (100 - horizontal_overcut_percent) / 100
    overcut_mm = bit_size * overcut_fraction
    y_increment = bit_size - overcut_mm
    # Always round up any fraction in passes calculation, rounding down would lead to material not being cut
    horizontal_passes = ceil((size_y - bit_size) / y_increment) 
    y_stride = ((size_y - bit_size) / horizontal_passes)


    # Create the list of Y axis start points
    y_start_points = [y + (y_stride * ndx) for ndx in range(horizontal_passes + 1)]

    cur_z = start_z

    while cur_z > start_z - size_z:
        nc_move_to_safe(nc_file)
        print(f'G0 X{x:.4f} Y{y:.4f}', file = nc_file)

        cur_z -= depth_per_pass
        if cur_z < start_z - size_z:
            cur_z = start_z - size_z
        print(f'G1 Z{cur_z:.4f} F{plunge_rate:.4f}', file = nc_file)

        left_to_right = True
        for cur_y in y_start_points:
            print(f'G1 Y{cur_y:.4f} F{feed_rate:.4f}', file = nc_file)
            if left_to_right:
                # Note the WHOLE bit size in the following x to compensate for the starting i/2
                print(f'G1 X{x + size_x - bit_size:.4f} F{feed_rate:.4f}', file = nc_file)
            else:
                print(f'G1 X{x:.4f} F{feed_rate:.4f}', file = nc_file)
            left_to_right = not left_to_right

def nc_offset_cut(nc_file, size_x, size_y, size_z, bit_size, overcut_percent = 33, feed_rate = 750.0, plunge_rate = 225.0, depth_per_pass = 0.5, start_x = 0, start_y = 0, start_z = 0, tool_centered = True):
    raise NotImplemented

    print('; Offset cut a level', file = nc_file)

    bit_radius = bit_size / 2


    # Calculate the offset for each pass to account for the overcut percentage
    overcut_fraction = 1 - (100 - overcut_percent) / 100
    overcut_mm = bit_size * overcut_fraction
    y_increment = bit_size - overcut_mm
    # Always round up any fraction in passes calculation, rounding down would lead to material not being cut
    horizontal_passes = ceil((size_y - bit_size) / y_increment) 
    y_stride = ((size_y - bit_size) / horizontal_passes)

    # Outward spiral cut going in clockwise direction starting at top right
    if tool_centered:
        # Move to bottom left of inner start of spiral
        x = start_x - (size_x / 2) + (bit_radius)
        y = start_y - (size_y / 2) + (bit_radius)
    else:
        x = start_x + (bit_radius)
        y = start_y + (bit_radius)

    cur_z = start_z

    while cur_z > start_z - size_z:
        nc_move_to_safe(nc_file)
        print(f'G0 X{x:.4f} Y{y:.4f}', file = nc_file)

        cur_z -= depth_per_pass
        if cur_z < start_z - size_z:
            cur_z = start_z - size_z
        print(f'G1 Z{cur_z:.4f} F{plunge_rate:.4f}', file = nc_file)

        left_to_right = True
        for cur_y in y_start_points:
            print(f'G1 Y{cur_y:.4f} F{feed_rate:.4f}', file = nc_file)
            if left_to_right:
                # Note the WHOLE bit size in the following x to compensate for the starting i/2
                print(f'G1 X{x + size_x - bit_size:.4f} F{feed_rate:.4f}', file = nc_file)
            else:
                print(f'G1 X{x:.4f} F{feed_rate:.4f}', file = nc_file)
            left_to_right = not left_to_right

bit_size = get_float_or_exit('Bit size (mm)', '3.175', min = 0.01, max = 3.175)
#if bit_size <= 0:
#    raise ValueError('Bit size must be greater than zero')
carve_width = get_float_or_exit('Carve width (X mm)', '10.0', min = bit_size, max = 1000)
#if carve_width < bit_size:
#    raise ValueError('Width of cutout must be greater than bit size')
carve_height = get_float_or_exit('Carve height (Y mm)', '10.0', min = bit_size, max = 1000)
#if carve_height < bit_size:
#    raise ValueError('Height of cutout must be greater than bit size')
overcut_percent = get_int_or_exit('Overcut percentage', '10', min = 10, max = 50)
#if overcut_percent < 10 or overcut_percent > 50:
#    raise ValueError('Overcut percentage must be between 10 and 50 percent')
carve_depth = get_float_or_exit('Carve depth (Z mm)', '1.0', min = 0.01)
#if carve_depth <= 0:
#    raise ValueError('Depth must be greater than zero')
depth_per_pass = get_float_or_exit('Depth per pass', '0.5', min = 0.01, max = 5)
#if depth_per_pass <= 0:
#    raise ValueError('Depth per pass must be greater than zero')
feed_rate = get_float_or_exit('Feed rate (mm per minute)', '800.0', min = 100, max = 1200)
#if feed_rate < 100 or feed_rate > 1200:
#    raise ValueError('Feed rate must be between 100 and 1200 mm per minute')

#cut_type: str = psg.popup_get_text('[R]aster or [O]ffset cut', default_text = 'R') # type: ignore
#cut_type = cut_type.upper()
#if cut_type != 'R' and cut_type != 'O':
#    raise ValueError('Cut type must be either [R]aster ot [O]ffset')
cut_type = 'R'

nc_file_name = psg.popup_get_file('Save gcode to', save_as = True, default_extension = '.nc', default_path = 'CutOut', file_types = (('GCode', '.nc'),))
outfile = open(nc_file_name, 'w')

nc_header(outfile)

if cut_type == 'R':
    nc_raster_cut(outfile, carve_width, carve_height, carve_depth, bit_size = bit_size, horizontal_overcut_percent = overcut_percent, depth_per_pass = depth_per_pass, feed_rate = feed_rate)
elif cut_type == 'O':
    nc_offset_cut(outfile, carve_width, carve_height, carve_depth, bit_size = bit_size, overcut_percent = overcut_percent, depth_per_pass = depth_per_pass, feed_rate = feed_rate)
    
nc_trailer(outfile)
outfile.close()