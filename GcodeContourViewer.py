import re

import PySimpleGUI as sg

from math import sqrt

GRAPH_WIDTH = 900
GRAPH_HEIGHT = 650
GRAPH_KEY = "-GRAPH-"
ESTIMATE_KEY = "-ESTIMATE-"


def load_toolpath(filename):
	"""Parse basic modal G0/G1 moves into absolute X/Y points."""
	points = []
	x = y = z = f = 0.0
	motion = None

	with open(filename, encoding = "utf-8", errors = "replace") as source:
		for line in source:
			line = re.sub(r"\([^)]*\)", "", line.split(";", 1)[0]).upper()
			words = re.findall(r"([A-Z])\s*(-?\d+(?:\.\d*)?)", line)
			for letter, value in words:
				if letter == "G" and float(value) in (0, 1):
					motion = int(float(value))

			axes = {letter: float(value) for letter, value in words if letter in ("X", "Y", "Z", "F")}
			if axes and motion is not None:
				x = axes.get("X", x)
				y = axes.get("Y", y)
				z = axes.get("Z", z)
				f = axes.get("F", f)
				points.append((x, y, z, f, motion))
	return points


def draw_toolpath(graph, points):
	graph_width, graph_height = graph.get_size()
	if graph_width <= 0 or graph_height <= 0:
		return

	graph.CanvasSize = (graph_width, graph_height)
	graph.change_coordinates((0, 0), (graph_width, graph_height))
	graph.erase()
	if not points or graph_width <= 40 or graph_height <= 40:
		return

	xs = [p[0] for p in points] + [0.0]
	ys = [p[1] for p in points] + [0.0]
	zs = [p[2] for p in points] + [0.0]
	min_x, max_x = min(xs), max(xs)
	min_y, max_y = min(ys), max(ys)
	min_z, max_z = min(zs), 0.0
	span_x, span_y, span_z = max(max_x - min_x, 1e-9), max(max_y - min_y, 1e-9), max(max_z - min_z, 1e-9)
	scale = min((graph_width - 40) / span_x, (graph_height - 40) / span_y)
	z_scale = -255 / span_z
	offset_x = (graph_width - span_x * scale) / 2
	offset_y = (graph_height - span_y * scale) / 2

	def canvas_point(px, py):
		return offset_x + (px - min_x) * scale, offset_y + (py - min_y) * scale

	previous = (0.0, 0.0)
	previous_z = 0.0
	processing_time = 0.0
	z_colour = 'blue'
	for x, y, z, f, motion in points:
		# Note the feed rate is reduced in the following processing time calculations
		# to allow for accelaration and decelaration of the axes motors
		if x == previous[0] and y == previous[1] and z != previous_z:
			processing_time += abs(z - previous_z) / (f * 0.8 / 60.0)
		elif (x != previous[0] or y != previous[1]) and z == previous_z:
			processing_time += sqrt((abs(x - previous[0]) ** 2) + (abs(y - previous[1]) ** 2)) / (f * 0.7 / 60.0)
		elif x == previous[0] and y == previous[1] and z == previous_z:
			pass
		else:
			raise RuntimeError(f'Processing time calculation found {x = } {y = } {z = } {f = }')
		z_colour = f'#{int((min_z - z) * z_scale):02X}0000'
		if motion == 1:
			graph.draw_line(canvas_point(*previous), canvas_point(x, y), z_colour, width=2)
		previous = (x, y)
		previous_z = z

	return processing_time


def main():
	sg.theme("SystemDefault")
	layout = [
		[sg.Text("G-code file:"), sg.Input(key = "-FILE-", expand_x = True),
		 sg.FileBrowse("Browse", file_types = (("G-code files", "*.nc;*.gcode"), ("All files", "*.*"))),
		 sg.Button("Display", key = "-DISPLAY-")],
		[sg.Graph(canvas_size = (GRAPH_WIDTH, GRAPH_HEIGHT),
				  graph_bottom_left = (0, 0), graph_top_right = (GRAPH_WIDTH, GRAPH_HEIGHT),
				  background_color = "white", key = GRAPH_KEY, expand_x = True, expand_y = True)],
		[sg.Text("High points red. All material cut away black")],
		[sg.Text("Estimated processing time ", key = ESTIMATE_KEY)]
	]
	window = sg.Window("G-code 2.5/3D Viewer", layout, resizable = True, finalize = True)
	graph = window[GRAPH_KEY]
	estimate = window[ESTIMATE_KEY]
	points = []

	def redraw_on_resize(event):
		if (event.width, event.height) != graph.CanvasSize: # type: ignore
			draw_toolpath(graph, points)

	graph.Widget.bind("<Configure>", redraw_on_resize, add = "+") # type: ignore

	while True:
		event, values = window.read()
		if event == sg.WIN_CLOSED:
			break
		if event == "-DISPLAY-":
			filename = values["-FILE-"]
			if not filename:
				sg.popup("Select a G-code file first.")
				continue
			try:
				points = load_toolpath(filename)
				estimated_time = draw_toolpath(graph, points)
				estimate.update(value = f'Estimated processing time {int(estimated_time / 3600)}:{int(estimated_time / 60) % 60:02}:{int(estimated_time) %60:02}') # type: ignore
			except OSError as error:
				sg.popup_error(f"Could not read the file:\n{error}")

	window.close()


if __name__ == "__main__":
	main()
