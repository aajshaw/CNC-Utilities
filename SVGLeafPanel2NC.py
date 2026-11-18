#!/usr/bin/env python3
"""Convert SVG <path> elements to basic CNC G-code."""

import argparse
import math
import re
import sys
import xml.etree.ElementTree as ET
from WorkPiece import WorkPiece, Bit

TOKEN = re.compile(r"[A-Za-z]|[-+]?(?:\d*\.\d+|\d+\.?\d*)(?:[eE][-+]?\d+)?")


def matrix_mul(a, b):
	return (a[0]*b[0] + a[2]*b[1], a[1]*b[0] + a[3]*b[1],
			a[0]*b[2] + a[2]*b[3], a[1]*b[2] + a[3]*b[3],
			a[0]*b[4] + a[2]*b[5] + a[4],
			a[1]*b[4] + a[3]*b[5] + a[5])


def transforms(text):
	result = (1, 0, 0, 1, 0, 0)
	for name, raw in re.findall(r"([A-Za-z]+)\s*\(([^)]*)\)", text or ""):
		v = [float(x) for x in TOKEN.findall(raw)]
		name = name.lower()
		if name == "matrix" and len(v) == 6:
			item = tuple(v)
		elif name == "translate" and v:
			item = (1, 0, 0, 1, v[0], v[1] if len(v) > 1 else 0)
		elif name == "scale" and v:
			item = (v[0], 0, 0, v[1] if len(v) > 1 else v[0], 0, 0)
		elif name == "rotate" and v:
			angle = math.radians(v[0])
			c, s = math.cos(angle), math.sin(angle)
			rotation = (c, s, -s, c, 0, 0)
			if len(v) >= 3:
				x, y = v[1:3]
				item = matrix_mul(matrix_mul((1, 0, 0, 1, x, y), rotation),
								  (1, 0, 0, 1, -x, -y))
			else:
				item = rotation
		elif name == "skewx" and v:
			item = (1, 0, math.tan(math.radians(v[0])), 1, 0, 0)
		elif name == "skewy" and v:
			item = (1, math.tan(math.radians(v[0])), 0, 1, 0, 0)
		else:
			continue
		result = matrix_mul(result, item)
	return result


def transform_point(point, m):
	x, y = point
	return m[0]*x + m[2]*y + m[4], m[1]*x + m[3]*y + m[5]


def arc(start, rx, ry, rotation, large, sweep, end):
	"""Approximate an SVG elliptical arc with short straight segments."""
	x1, y1 = start
	x2, y2 = end
	rx, ry = abs(rx), abs(ry)
	if not rx or not ry or start == end:
		return [end]
	phi = math.radians(rotation % 360)
	cp, sp = math.cos(phi), math.sin(phi)
	dx, dy = (x1-x2)/2, (y1-y2)/2
	xp, yp = cp*dx + sp*dy, -sp*dx + cp*dy
	scale = xp*xp/(rx*rx) + yp*yp/(ry*ry)
	if scale > 1:
		rx, ry = rx*math.sqrt(scale), ry*math.sqrt(scale)
	numerator = max(0, rx*rx*ry*ry-rx*rx*yp*yp-ry*ry*xp*xp)
	denominator = rx*rx*yp*yp + ry*ry*xp*xp
	factor = 0 if denominator == 0 else math.sqrt(numerator/denominator)
	if bool(large) == bool(sweep):
		factor = -factor
	cxp, cyp = factor*rx*yp/ry, factor*-ry*xp/rx
	cx, cy = cp*cxp-sp*cyp+(x1+x2)/2, sp*cxp+cp*cyp+(y1+y2)/2
	u, w = ((xp-cxp)/rx, (yp-cyp)/ry), ((-xp-cxp)/rx, (-yp-cyp)/ry)
	theta = math.atan2(u[1], u[0])
	delta = math.atan2(u[0]*w[1]-u[1]*w[0], u[0]*w[0]+u[1]*w[1])
	if not sweep and delta > 0:
		delta -= 2*math.pi
	elif sweep and delta < 0:
		delta += 2*math.pi
	count = max(2, math.ceil(abs(delta)/(math.pi/18)))
	result = []
	for i in range(1, count+1):
		t = theta + delta*i/count
		result.append((cx+rx*cp*math.cos(t)-ry*sp*math.sin(t),
					   cy+rx*sp*math.cos(t)+ry*cp*math.sin(t)))
	result[-1] = end
	return result

# Note that Y axis is negative
def get_digonal(paths):
	first_point = paths[0][0]
	x_min = x_max = first_point[0]
	y_min = y_max = first_point[1]

	for path in paths:
		for point in path:
			x = point[0]
			y = abs(point[1])
			if x < x_min:
				x_min = x
			if x > x_max:
				x_max = x
			if y < y_min:
				y_min = y
			if y > y_max:
				y_max = y

	y_min *= -1
	y_max *= -1

	return (x_min, y_min), (x_max, y_max)

def get_path_diagonal(path):
#	print(f'{path = }')
	x_min = x_max = path[0][0]
	y_min = y_max = path[0][1]

	for point in path:
		x = point[0]
		y = abs(point[1])
		if x < x_min:
			x_min = x
		if x > x_max:
			x_max = x
		if y < y_min:
			y_min = y
		if y > y_max:
			y_max = y

	y_min *= -1
	y_max *= -1

	return (x_min, y_min), (x_max, y_max)

def center_paths(paths, top_left, bottom_right):
	# Note: at this stage the Y axis is inverted
	width = bottom_right[0] - top_left[0]
	height = top_left[1] - bottom_right[1]

	# First offset is to get the top left to (0, 0)
	x_offset = 0 - top_left[0] # shunt left
	y_offset = 0 + top_left[1] # shunt up

	# Then offset to the center of the rectangle defined by top left and bottom right
	x_offset -= width / 2.0 # shunt left
	y_offset -= height / 2.0 # shunt up

	new_paths = []

	# Apply the offsets to every point in the paths
	for path in paths:
		new_points = []
		for point in path:
			new_points.append((point[0] + x_offset, point[1] + y_offset))
		new_paths.append(new_points)

	return new_paths


def pop_outer_frame(paths):
	# The outer path (the containing box) is always the first path and should consist of 5 elements, the first 'move to start' then the four to each corner
	if len(paths[0]) == 5:
		return paths.pop(0)
	else:
		raise RuntimeError('Outer frame not found')

def parse_path(data):
	tokens = TOKEN.findall(data or "")
	paths, points = [], []
	i, command = 0, None
	current = (0.0, 0.0)
	start = current
	cubic_control = quad_control = None

	def read(count):
		nonlocal i
		if i + count > len(tokens) or any(t.isalpha() for t in tokens[i:i+count]):
			raise ValueError("Incomplete SVG path command")
		values = [float(t) for t in tokens[i:i+count]]
		i += count
		return values

	while i < len(tokens):
		if tokens[i].isalpha():
			command = tokens[i]
			i += 1
			if command in "Zz":
				if points:
					if points[-1] != start:
						points.append(start)
					paths.append(points)
					points = []
				current = start
				cubic_control = quad_control = None
				command = None
				continue
		if command is None or command.upper() not in "MLHVCSQTA":
			raise ValueError("Unsupported or missing SVG path command")
		op, relative, old = command.upper(), command.islower(), current
		if op in "ML":
			x, y = read(2)
			current = (old[0]+x, old[1]+y) if relative else (x, y)
			if op == "M":
				if points:
					paths.append(points)
				points, start = [current], current
				command = "l" if relative else "L"
			else:
				points.append(current)
		elif op == "H":
			x, = read(1)
			current = (old[0]+x if relative else x, old[1])
			points.append(current)
		elif op == "V":
			y, = read(1)
			current = (old[0], old[1]+y if relative else y)
			points.append(current)
		elif op in "CS":
			if op == "C":
				x1, y1, x2, y2, x, y = read(6)
				control1 = (old[0]+x1, old[1]+y1) if relative else (x1, y1)
			else:
				control1 = ((2*old[0]-cubic_control[0], 2*old[1]-cubic_control[1])
							if cubic_control else old)
				x2, y2, x, y = read(4)
			control2 = (old[0]+x2, old[1]+y2) if relative else (x2, y2)
			end = (old[0]+x, old[1]+y) if relative else (x, y)
			for n in range(1, 21):
				t, q = n/20, 1-n/20
				points.append((q**3*old[0]+3*q*q*t*control1[0]+3*q*t*t*control2[0]+t**3*end[0],
							   q**3*old[1]+3*q*q*t*control1[1]+3*q*t*t*control2[1]+t**3*end[1]))
			current, cubic_control, quad_control = end, control2, None
			continue
		elif op in "QT":
			if op == "Q":
				x1, y1, x, y = read(4)
				control = (old[0]+x1, old[1]+y1) if relative else (x1, y1)
			else:
				control = ((2*old[0]-quad_control[0], 2*old[1]-quad_control[1])
						   if quad_control else old)
				x, y = read(2)
			end = (old[0]+x, old[1]+y) if relative else (x, y)
			for n in range(1, 21):
				t, q = n/20, 1-n/20
				points.append((q*q*old[0]+2*q*t*control[0]+t*t*end[0],
							   q*q*old[1]+2*q*t*control[1]+t*t*end[1]))
			current, quad_control, cubic_control = end, control, None
			continue
		elif op == "A":
			rx, ry, rotation, large, sweep, x, y = read(7)
			end = (old[0]+x, old[1]+y) if relative else (x, y)
			points.extend(arc(old, rx, ry, rotation, large, sweep, end))
			current, cubic_control, quad_control = end, None, None
			continue
		if op not in "CS":
			cubic_control = None
		if op not in "QT":
			quad_control = None
	if points:
		paths.append(points)
	return [p for p in paths if len(p) > 1]


def read_svg(filename):
	root = ET.parse(filename).getroot()
	paths = []

	def visit(element, parent):
		matrix = matrix_mul(parent, transforms(element.get("transform", "")))
		if element.tag.rsplit("}", 1)[-1] == "path" and element.get("d"):
			paths.extend([[transform_point(p, matrix) for p in line]
						  for line in parse_path(element.get("d"))])
		for child in element:
			visit(child, matrix)

	visit(root, (1, 0, 0, 1, 0, 0))
	return paths


def make_gcode(work_piece: WorkPiece, paths, scale, frame, safe_z, pass_z, cut_z, feed, flip_y):
	lines = work_piece.gcode_header()
	lines += work_piece.gcode_safe_z()
	for path in paths:
		points = [(x * scale, (-y if flip_y else y) * scale) for x, y in path]
		x, y = points[0]
		use_z = 0.0
		done = False
		while not done:
			use_z += pass_z
			if use_z < cut_z:
				use_z = cut_z
				done = True
			lines.extend((f"G0 X{x:.3f} Y{y:.3f}", f"G1 Z{use_z:.3f} F{feed:.3f}"))
			lines.extend(f"G1 X{x:.3f} Y{y:.3f} F{feed:.3f}" for x, y in points[1:])
		lines.append(f"G0 Z{safe_z:.3f}")

	# Add the frame
	lines.append(f'; Frame; width {frame[0]} height {frame[1]}')
	x = frame[0] / 2.0
	y = frame[1] / 2.0
	use_z = 0.0
	done = False
	while not done:
		use_z += pass_z
		if use_z < cut_z:
			use_z = cut_z
			done = True
		lines.append(f'G0 X{x * -1:.3f} Y{y * -1:.3f}')
		lines.append(f'G1 Z{use_z:.3f} F{feed:.3f}')
		lines.append(f'G1 X{x:.3f} Y{y * -1:.3f} F{feed:.3f}')
		lines.append(f'G1 X{x:.3f} Y{y:.3f} F{feed:.3f}')
		lines.append(f'G1 X{x * -1:.3f} Y{y:.3f} F{feed:.3f}')
		lines.append(f'G1 X{x * -1:.3f} Y{y * -1:.3f} F{feed:.3f}')
	lines.append(f'G0 Z{safe_z:.3f}')

	lines += work_piece.gcode_trailer()
	return "\n".join(lines) + "\n"


def main():
	parser = argparse.ArgumentParser(description = "Convert SVG Leaf Panel paths to G-code.")
	parser.add_argument("input", help = "input SVG Leaf Panel file")
	parser.add_argument("output", help = "output G-code file")
	parser.add_argument("-x-scale-to", type = float, default = 100.0, help = "size that x axis should scale to in mm")
	parser.add_argument("-frame-size", type = float, default = 20.0, help = "size of the frame in mm")
	parser.add_argument("-safe-z", type = float, default = 5.0, help = "safe height in mm")
	parser.add_argument("-cut-z", type = float, default = -1.0, help = "total cut depth in mm (negative)")
	parser.add_argument("-pass-z", type = float, default = -0.7, help = "cut depth per pass in mm (negative)")
	parser.add_argument("-feed", type = float, default = 300.0, help = "cut feed in mm/min")
	parser.add_argument("-invert-y", action = "store_true", help = "invert the SVG Y axis")
	args = parser.parse_args()
	if args.safe_z <= 0.0 or args.cut_z >= 0.0 or args.pass_z >= 0.0:
		parser.error("safe-z must be positive, cut-z and pass-z must be negative")
	if args.feed <= 0 or args.safe_z <= args.cut_z or args.pass_z < args.cut_z:
		print(f'{args.feed = } {args.safe_z = } {args.cut_z = } { args.pass_z = }')
		parser.error("scale and feed must be positive, safe-z must be above cut-z and pass-z must be less than or eqial to cut-z")
	if args.x_scale_to < 100.0:
		parser.error('x-scale-to must be at least than 100.0mm')
	if args.frame_size < 20.0:
		parser.error('frame-size must be at least 20.0mm')
	try:
		paths = read_svg(args.input)
		if not paths:
			raise ValueError("No SVG path geometry found")
		pop_outer_frame(paths)
		top_left, bottom_right = get_digonal(paths)
		scale = (args.x_scale_to - (2 * args.frame_size)) / abs(bottom_right[0] - top_left[0])
		frame = ((scale * abs(bottom_right[0] - top_left[0])) + (2 * args.frame_size), (scale * abs(bottom_right[1] - top_left[1])) + (2 * args.frame_size))
		paths = center_paths(paths, top_left, bottom_right)

		work_piece = WorkPiece(args.output, creator = f'Generated by {__file__}', material = 'MDF', thickness = args.cut_z * -1, width = frame[0], height = frame[1], safe_z = args.safe_z, feed_rate = args.feed) # type: ignore
		with open(args.output, "w", encoding="utf-8", newline="\n") as output:
			output.write(make_gcode(work_piece, paths, scale, frame, args.safe_z, args.pass_z, args.cut_z, args.feed, args.invert_y))
		print(f'Width {frame[0]}, Height {frame[1]}')
	except (OSError, ET.ParseError, ValueError) as error:
		print(f"SVGLeafPanel2NC: {error}", file=sys.stderr)
		return 1
	return 0


if __name__ == "__main__":
	raise SystemExit(main())
